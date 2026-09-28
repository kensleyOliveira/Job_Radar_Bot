import asyncio
from app.infrastructure.database.session import init_db

async def run():
    print("Criando tabelas no PostgreSQL...")
    await init_db()
    print("Tabelas criadas com sucesso!")

if __name__ == "__main__":
    asyncio.run(run())