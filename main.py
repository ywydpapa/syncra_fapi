import os
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

# SQLAlchemy 비동기 관련 모듈
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.future import select

# 1. 환경 변수 로드
load_dotenv()
DB_URL = os.getenv("dburl")

# 2. 데이터베이스 설정
engine = create_async_engine(DB_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


# 3. 테이블 모델 정의
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
    regDate = Column(DateTime)  # 읽기 전용이므로 default 설정 불필요
    dmsA = Column(Integer)
    dmsB = Column(Integer)
    dmsC = Column(Integer)
    dmsD = Column(Integer)
    attrib = Column(String(10))


# 4. FastAPI 앱 및 템플릿 설정
app = FastAPI()
templates = Jinja2Templates(directory="templates")


# 5. 메인 페이지 (웹 접속 시 DB에서 데이터 읽어오기)
@app.get("/")
async def view_ais_data(request: Request):
    async with AsyncSessionLocal() as session:
        # DB에서 데이터 읽어오기 (예: 최근 등록된 순으로 100개)
        stmt = select(StvAIS).order_by(StvAIS.regDate.desc()).limit(100)
        result = await session.execute(stmt)
        ships = result.scalars().all()

    # ✅ 수정된 부분: request, name, context 키워드를 명시적으로 적어주어야 에러가 나지 않습니다.
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request, "ships": ships}
    )


# 6. 실시간 갱신용 API (프론트엔드에서 주기적으로 호출)
@app.get("/api/ships")
async def get_ships_api():
    async with AsyncSessionLocal() as session:
        stmt = select(StvAIS).order_by(StvAIS.regDate.desc()).limit(100)
        result = await session.execute(stmt)
        ships = result.scalars().all()

        # JSON 형태로 변환하여 반환
        ship_list = []
        for ship in ships:
            ship_list.append({
                "mmsi": ship.mmsi,
                "vesselName": ship.vesselName,
                "callSign": ship.callSign,
                "imoNo": ship.imoNo,
                "destination": ship.destination,
                "eta": ship.eta,
                "vesselType": ship.vesselType,
                "draft": ship.draft,
                "regDate": ship.regDate.strftime('%Y-%m-%d %H:%M:%S') if ship.regDate else "",
                "dmsA": ship.dmsA,
                "dmsB": ship.dmsB,
                "dmsC": ship.dmsC,
                "dmsD": ship.dmsD,
                "attrib": ship.attrib
            })
        return ship_list
