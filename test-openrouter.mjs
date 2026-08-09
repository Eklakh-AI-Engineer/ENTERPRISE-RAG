import { OpenRouter } from "@openrouter/sdk";

const openrouter = new OpenRouter({
  apiKey: process.env.OPENROUTER_API_KEY
});

const stream = await openrouter.chat.send({
  chatRequest: {
    model: "google/gemma-4-26b-a4b-it:free",
    messages: [
      {
        role: "user",
        content: "How many r's are in the word 'strawberry'?"
      }
    ],
    stream: true
  }
});

for await (const chunk of stream) {
  const content = chunk.choices[0]?.delta?.content;

  if (content) {
    process.stdout.write(content);
  }

  if (chunk.usage) {
    console.log(
      "\nReasoning tokens:",
      chunk.usage.completionTokensDetails?.reasoningTokens
    );
  }
}