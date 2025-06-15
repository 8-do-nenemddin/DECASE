from app.database import Base, engine
from app.models import *  # 모든 모델을 임포트

def init_db():
    print("데이터베이스 테이블을 생성합니다...")
    Base.metadata.create_all(bind=engine)
    print("데이터베이스 테이블 생성이 완료되었습니다.")

if __name__ == "__main__":
    init_db() 