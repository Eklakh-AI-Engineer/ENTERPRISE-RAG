from app.generation.openrouter import OpenRouterClient


def main():

    llm = OpenRouterClient()

    response = llm.generate(
        "Reply with exactly: OpenRouter connection successful."
    )

    print("\nLLM RESPONSE:")
    print(response)


if __name__ == "__main__":
    main()