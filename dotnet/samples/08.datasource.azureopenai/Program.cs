﻿using Microsoft.Bot.Builder;
using Microsoft.Bot.Builder.Integration.AspNet.Core;
using Microsoft.Bot.Connector.Authentication;
using Microsoft.Teams.AI.AI.Models;
using Microsoft.Teams.AI.AI.Planners;
using Microsoft.Teams.AI.AI.Prompts;
using Microsoft.Teams.AI.State;
using Microsoft.Teams.AI;
using AzureOpenAIBot;
using Microsoft.Teams.AI.AI;
using Azure.Identity;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddHttpClient("WebClient", client => client.Timeout = TimeSpan.FromSeconds(600));
builder.Services.AddHttpContextAccessor();

// Prepare Configuration for ConfigurationBotFrameworkAuthentication
var config = builder.Configuration.Get<ConfigOptions>()!;
builder.Configuration["MicrosoftAppType"] = "MultiTenant";
builder.Configuration["MicrosoftAppId"] = config.BOT_ID;
builder.Configuration["MicrosoftAppPassword"] = config.BOT_PASSWORD;

// Create the Bot Framework Authentication to be used with the Bot Adapter.
builder.Services.AddSingleton<BotFrameworkAuthentication, ConfigurationBotFrameworkAuthentication>();

// Create the Cloud Adapter with error handling enabled.
// Note: some classes expect a BotAdapter and some expect a BotFrameworkHttpAdapter, so
// register the same adapter instance for all types.
builder.Services.AddSingleton<TeamsAdapter, AdapterWithErrorHandler>();
builder.Services.AddSingleton<IBotFrameworkHttpAdapter>(sp => sp.GetService<TeamsAdapter>()!);
builder.Services.AddSingleton<BotAdapter>(sp => sp.GetService<TeamsAdapter>()!);

builder.Services.AddSingleton<IStorage, MemoryStorage>();

// Create AI Model
if (!string.IsNullOrEmpty(config.OpenAI?.ApiKey))
{
    // Create OpenAI Model
    builder.Services.AddSingleton<OpenAIModel>(sp => new(
        new OpenAIModelOptions(config.OpenAI.ApiKey, "gpt-3.5-turbo")
        {
            LogRequests = true
        },
        sp.GetService<ILoggerFactory>()
    ));
}
else if (!string.IsNullOrEmpty(config.Azure?.OpenAIEndpoint))
{
    if (!string.IsNullOrEmpty(config.Azure?.OpenAIApiKey))
    {
        // Create Azure OpenAI Model with API Key Auth
        builder.Services.AddSingleton<OpenAIModel>(sp => new(
            new AzureOpenAIModelOptions(
                config.Azure.OpenAIApiKey,
                "gpt-35-turbo",
                config.Azure.OpenAIEndpoint
            )
            {
                LogRequests = true
            },
            sp.GetService<ILoggerFactory>()
        ));
    }
    else
    {
        // Create Azure OpenAI Model with Managed Identity Auth
        builder.Services.AddSingleton<OpenAIModel>(sp => new(
            new AzureOpenAIModelOptions(
                new DefaultAzureCredential(),
                "gpt-4o",
                config.Azure!.OpenAIEndpoint
            )
            {
                LogRequests = true
            },
            sp.GetService<ILoggerFactory>()
        ));
    }
}
else
{
    throw new Exception("please configure settings for either OpenAI or Azure");
}

// Create the bot as transient. In this case the ASP Controller is expecting an IBot.
builder.Services.AddTransient<IBot>(sp =>
{
    // Create loggers
    ILoggerFactory loggerFactory = sp.GetService<ILoggerFactory>()!;

    // Create Prompt Manager
    PromptManager prompts = new(new()
    {
        PromptFolder = "./Prompts"
    });

    // Create ActionPlanner
    ActionPlanner<TurnState> planner = new(
        options: new(
            model: sp.GetService<OpenAIModel>()!,
            prompts: prompts,
            defaultPrompt: async (context, state, planner) =>
            {
                PromptTemplate template = prompts.GetPrompt("Chat");
                return await Task.FromResult(template);
            }
        )
        { LogRepairs = true },
        loggerFactory: loggerFactory
    );

    AIOptions<TurnState> options = new(planner);
    options.EnableFeedbackLoop = true;

    Application<TurnState> app = new ApplicationBuilder<TurnState>()
        .WithAIOptions(options)
        .WithStorage(sp.GetService<IStorage>()!)
        .Build();

    app.OnMessage("/reset", async (turnContext, turnState, _) =>
    {
        turnState.DeleteConversationState();
        await turnContext.SendActivityAsync("The conversation state has been reset");
    });

    app.OnFeedbackLoop((turnContext, turnState, feedbackLoopData, _) =>
    {
        if (feedbackLoopData.ActionValue?.Reaction == "like")
        {
            Console.WriteLine("Like");
        }
        else
        {
            Console.WriteLine("Dislike");
        }

        return Task.CompletedTask;
    });

    return app;
});

var app = builder.Build();

if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
}

app.UseStaticFiles();
app.UseRouting();
app.MapControllers();

app.Run();
