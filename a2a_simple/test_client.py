import asyncio

import httpx
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import display_agent_card, new_text_message
from a2a.types.a2a_pb2 import Role, SendMessageRequest
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH


async def main() -> None:
    base_url = "http://127.0.0.1:9999"

    async with httpx.AsyncClient() as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)

        print(
            f"Attempting to fetch public card from {base_url}{AGENT_CARD_WELL_KNOWN_PATH}"
        )
        public_card = await resolver.get_agent_card()
        display_agent_card(public_card)
        print(public_card.supported_interfaces)

        print("Non-streaming call...")
        config = ClientConfig(streaming=False)
        client = await create_client(agent=public_card, client_config=config)
        print("Non-streaming client initialized.")

        message = new_text_message("Say hello", role=Role.ROLE_USER)
        request = SendMessageRequest(message=message)

        print("Response:\n")
        async for chunk in client.send_message(request):
            print(chunk)

        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
