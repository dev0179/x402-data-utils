import asyncio
from eth_account import Account
from x402.clients.httpx import x402HttpxClient  # type: ignore

async def main():
    acct = Account.from_key("YOUR_PRIVATE_KEY")
    async with x402HttpxClient(account=acct, base_url="http://127.0.0.1:8000") as client:
        r = await client.get("/health")
        print(r.status_code, r.json())

        r2 = await client.post("/summarize/logs", content=b"ERROR db timeout\nERROR db timeout\n")
        print(r2.status_code, r2.json())

if __name__ == "__main__":
    asyncio.run(main())
