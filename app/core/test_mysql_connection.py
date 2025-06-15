import asyncio
from app.core.mysql_config import async_engine, get_db
from sqlalchemy import text

async def test_connection():
    try:
        # 데이터베이스 연결 테스트
        async with async_engine.connect() as conn:
            # 테이블 목록 조회
            result = await conn.execute(text("SHOW TABLES"))
            tables = result.fetchall()
            
            print("✅ 데이터베이스 연결 성공!")
            print("\n현재 데이터베이스의 테이블 목록:")
            for table in tables:
                print(f"- {table[0]}")
                
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_connection()) 