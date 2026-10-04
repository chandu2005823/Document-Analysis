import os
from groq import Groq


def get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY environment variable is not set."
        )

    return Groq(api_key=api_key)


def generate_answer(prompt):

    client = get_groq_client()

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    return response.choices[0].message.content


if __name__ == "__main__":

    prompt = """
    Explain what Retrieval-Augmented Generation (RAG) is
    in three simple sentences.
    """

    answer = generate_answer(prompt)

    print("\nGroq Response:")
    print(answer)
