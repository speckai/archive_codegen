import asyncio
import os
from typing import Union

import instructor
from pydantic import BaseModel, Field


class Highway(BaseModel):
    name: str = Field(
        ...,
        description="The name of the highway.",
    )


class Car(BaseModel):
    name: str = Field(
        ...,
        description="The name of the car.",
    )


class Exit(BaseModel):
    name: str = Field(
        ...,
        description="The name of the exit.",
    )


class PopulatedRoad(BaseModel):
    steps: list[Union[Exit, Car]] = Field(
        ...,
        description="The steps of the road.",
    )


if __name__ == "__main__":

    async def main():
        from anthropic import AsyncAnthropic

        async_client = instructor.from_anthropic(
            AsyncAnthropic(
                api_key=os.getenv("ANTHROPIC_API_KEY"),
            ),
            mode=instructor.Mode.ANTHROPIC_JSON,
        )

        response_gen = async_client.messages.create_partial(
            system="You are a helpful assistant that creates populated roads.",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Create a populated road. Has to have at least 10 unique steps.",
                        }
                    ],
                }
            ],
            model="claude-3-5-sonnet-20241022",
            response_model=PopulatedRoad,
            max_tokens=2000,
            stream=True,
        )

        async for chunk in response_gen:
            print(chunk)

    asyncio.run(main())
