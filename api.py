import os
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, select
from dotenv import load_dotenv

# 1. 환경 변수 및 DB 설정
load_dotenv()
DB_URL = os.getenv("dburl")

engine = create_async_engine(DB_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


# 2. 테이블 모델 정의 (기존과 동일)
class StvAIS(Base):
    __tablename__ = 'stvAIS'

    mmsi = Column(Integer, primary_key=True)
    vesselName = Column(String(100))
    callSign = Column(String(50))
    imoNo = Column(Integer)
    destination = Column(String(100))
    eta = Column(String(50))
    vesselType = Column(Integer)
    draft = Column(Float)
    regDate = Column(DateTime)
    attrib = Column(String(50))
    dmsA = Column(Integer)
    dmsB = Column(Integer)
    dmsC = Column(Integer)
    dmsD = Column(Integer)


# 3. FastAPI 앱 및 템플릿 설정
app = FastAPI(title="AIS Data Viewer")
templates = Jinja2Templates(directory="templates")  # templates 폴더 지정


# 4. 메인 페이지 라우터
@app.get("/")
async def view_ais_data(request: Request):
    async with AsyncSessionLocal() as session:
        # 최근 업데이트(regDate)된 순서대로 100건을 조회
        stmt = select(StvAIS).order_by(StvAIS.regDate.desc()).limit(100)
        result = await session.execute(stmt)
        ships = result.scalars().all()

    # index.html 템플릿에 ships 데이터를 전달하여 렌더링
    return templates.TemplateResponse("index.html", {"request": request, "ships": ships})
