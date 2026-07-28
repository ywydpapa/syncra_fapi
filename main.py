import os
import httpx
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv

# SQLAlchemy 비동기 관련 모듈
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from sqlalchemy.future import select

# ==========================================
# 1. 환경 변수 로드
# ==========================================
load_dotenv()
DB_URL = os.getenv("dburl")
VESSEL_API_KEY = os.getenv("VESSEL_API_KEY", "your_vesselapi_key_here")  # .env에 추가 필요
VESSEL_API_BASE_URL = "https://api.vesselapi.com/v1"

# ==========================================
# 2. 데이터베이스 설정 (비동기)
# ==========================================
engine = create_async_engine(DB_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


# ==========================================
# 3. 테이블 모델 정의
# ==========================================
# (기존) AIS 데이터 테이블
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
    dmsA = Column(Integer)
    dmsB = Column(Integer)
    dmsC = Column(Integer)
    dmsD = Column(Integer)
    attrib = Column(String(10))


# (신규) 선박 제원 마스터 테이블
class VesselMst(Base):
    __tablename__ = "vesselMst"

    vesselNo = Column(Integer, primary_key=True, autoincrement=True)
    imoNo = Column(String(7), unique=True, index=True, nullable=False)
    vesselMmsi = Column(String(20), nullable=True)
    vesselName = Column(String(255), nullable=True)
    callSign = Column(String(50), nullable=True)
    vesselType = Column(String(100), nullable=True)
    vesselFlag = Column(String(100), nullable=True)
    buildYear = Column(Integer, nullable=True)
    grossTonnage = Column(Integer, nullable=True)
    deadWeight = Column(Integer, nullable=True)
    lengthOverall = Column(Float, nullable=True)
    beam = Column(Float, nullable=True)
    draft = Column(Float, nullable=True)
    nameAis = Column(String(255), nullable=True)
    countryCode = Column(String(10), nullable=True)
    builder = Column(String(255), nullable=True)
    operatingStatus = Column(String(50), nullable=True)
    lengthUnit = Column(String(10), nullable=True)
    breadthUnit = Column(String(10), nullable=True)
    speedCalculatedAvg = Column(Float, nullable=True)
    speedObservedMax = Column(Float, nullable=True)
    draughtCalculatedAvg = Column(Float, nullable=True)
    classSociety = Column(String(100), nullable=True)
    ownerName = Column(String(255), nullable=True)
    managerName = Column(String(255), nullable=True)
    regDate = Column(DateTime, server_default=func.now())
    attrib = Column(String(20), default='1000010000', server_default='1000010000')


# ==========================================
# 4. Pydantic 스키마 (API 응답용)
# ==========================================
# main.py

class VesselResponse(BaseModel):
    vesselNo: Optional[int] = None
    imoNo: str
    vesselMmsi: Optional[str] = None
    vesselName: Optional[str] = None
    callSign: Optional[str] = None
    vesselType: Optional[str] = None
    vesselFlag: Optional[str] = None
    buildYear: Optional[int] = None
    grossTonnage: Optional[int] = None
    deadWeight: Optional[int] = None
    lengthOverall: Optional[float] = None
    beam: Optional[float] = None
    draft: Optional[float] = None
    nameAis: Optional[str] = None
    countryCode: Optional[str] = None
    builder: Optional[str] = None
    operatingStatus: Optional[str] = None
    lengthUnit: Optional[str] = None
    breadthUnit: Optional[str] = None
    speedCalculatedAvg: Optional[float] = None
    speedObservedMax: Optional[float] = None
    draughtCalculatedAvg: Optional[float] = None
    classSociety: Optional[str] = None
    ownerName: Optional[str] = None
    managerName: Optional[str] = None
    attrib: Optional[str] = None
    source: str = "Unknown"
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 5. 외부 API 호출 함수 (VesselAPI 연동)
# ==========================================
# main.py 의 fetch_vessel_from_api 함수를 아래 코드로 교체하세요.

# ==========================================
# 3. API 매핑 함수 수정 (fetch_vessel_from_api 함수 교체)
# ==========================================
async def fetch_vessel_from_api(imo: str) -> dict:
    url = f"https://api.vesselapi.com/v1/vessel/{imo}"
    headers = {"Authorization": f"Bearer {VESSEL_API_KEY}", "Accept": "application/json"}
    params1 = {"filter.idType": "imo"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, headers=headers, params=params1)
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="VesselAPI에서 선박을 찾을 수 없습니다.")
        elif response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"API Error: {response.text}")

        json_response = response.json()
        vessel_data = json_response.get("vessel", {})

        # 💡 API의 모든 데이터를 DB 컬럼명에 맞게 매핑
        return {
            "imoNo": str(vessel_data.get("imo", imo)),
            "vesselMmsi": str(vessel_data.get("mmsi")) if vessel_data.get("mmsi") else None,
            "callSign": vessel_data.get("call_sign"),
            "vesselName": vessel_data.get("name"),
            "nameAis": vessel_data.get("name_ais"),
            "vesselType": vessel_data.get("vessel_type"),
            "vesselFlag": vessel_data.get("country"),
            "countryCode": vessel_data.get("country_code"),
            "buildYear": vessel_data.get("year_built"),
            "builder": vessel_data.get("builder"),
            "operatingStatus": vessel_data.get("operating_status"),
            "lengthOverall": vessel_data.get("length"),
            "lengthUnit": vessel_data.get("length_unit"),
            "beam": vessel_data.get("breadth"),
            "breadthUnit": vessel_data.get("breadth_unit"),
            "grossTonnage": vessel_data.get("gross_tonnage"),
            "deadWeight": vessel_data.get("deadweight_tonnage"),
            "speedCalculatedAvg": vessel_data.get("speed_calculated_avg"),
            "speedObservedMax": vessel_data.get("speed_observed_max"),
            "draughtCalculatedAvg": vessel_data.get("draught_calculated_avg"),
            "draft": vessel_data.get("draught_observed_max"),
            "classSociety": vessel_data.get("class_society"),
            "ownerName": vessel_data.get("owner_name"),
            "managerName": vessel_data.get("manager_name")
        }


# ==========================================
# 6. FastAPI 앱 및 템플릿 설정
# ==========================================
app = FastAPI()
templates = Jinja2Templates(directory="templates")


# ==========================================
# 7. 라우터 (Endpoints)
# ==========================================
# (기존) 메인 페이지
@app.get("/")
async def view_ais_data(request: Request):
    async with AsyncSessionLocal() as session:
        stmt = select(StvAIS).order_by(StvAIS.regDate.desc()).limit(100)
        result = await session.execute(stmt)
        ships = result.scalars().all()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request, "ships": ships}
    )


# (기존) 실시간 갱신용 API
@app.get("/api/ships")
async def get_ships_api():
    async with AsyncSessionLocal() as session:
        stmt = select(StvAIS).order_by(StvAIS.regDate.desc()).limit(100)
        result = await session.execute(stmt)
        ships = result.scalars().all()

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


# (신규) 선박 제원 조회 및 캐싱 API
@app.get("/api/vessels/{imo}", response_model=VesselResponse)
async def get_vessel_info(imo: str):
    if not imo.isdigit() or len(imo) != 7:
        raise HTTPException(status_code=400, detail="Invalid IMO number format")

    async with AsyncSessionLocal() as session:
        # 1. MariaDB에서 검색
        stmt = select(VesselMst).where(VesselMst.imoNo == imo)
        result = await session.execute(stmt)
        db_vessel = result.scalars().first()

        if db_vessel:
            response_data = VesselResponse.model_validate(db_vessel) if hasattr(VesselResponse, 'model_validate') else VesselResponse.from_orm(db_vessel)
            response_data.source = "MariaDB Cache"
            return response_data

        # 2. DB에 없으면 외부 API 호출 (여기서 이미 DB 컬럼명에 맞게 매핑되어 반환됨)
        api_data = await fetch_vessel_from_api(imo)

        # 3. MariaDB에 저장
        # 💡 수정됨: api_data가 이미 완벽한 매핑 형태이므로 바로 **api_data로 넣습니다.
        new_vessel = VesselMst(**api_data)
        session.add(new_vessel)
        await session.commit()
        await session.refresh(new_vessel)

        # 4. 결과 반환
        response_data = VesselResponse.model_validate(new_vessel) if hasattr(VesselResponse, 'model_validate') else VesselResponse.from_orm(new_vessel)
        response_data.source = "VesselAPI (Newly Cached)"
        return response_data

