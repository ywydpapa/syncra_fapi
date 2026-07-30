import os
import httpx
import asyncio
import json  # 🌟 추가됨: AI 응답을 JSON으로 파싱하기 위해 필요
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv
import time
from google import genai

# SQLAlchemy 비동기 관련 모듈
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from sqlalchemy.future import select

# ==========================================
# 1. 환경 변수 로드 및 AI 클라이언트 설정
# ==========================================
load_dotenv()
DB_URL = os.getenv("dburl")
VESSEL_API_KEY = os.getenv("VESSEL_API_KEY", "your_vesselapi_key_here")
VESSEL_API_BASE_URL = "https://api.vesselapi.com/v1"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# ==========================================
# 2. 데이터베이스 설정 (비동기)
# ==========================================
engine = create_async_engine(DB_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


# ==========================================
# 3. 테이블 모델 정의
# ==========================================
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
# 6. 🌟 AI 부산항 판별 로직 (일괄 처리 - 10초 주기 제한)
# ==========================================
busan_dest_cache = {}
api_semaphore = asyncio.Semaphore(1)
api_cooldown_until = 0  # 다음 API 호출이 가능한 시간


async def update_busan_cache_batch(destinations: set):
    global api_cooldown_until
    if not ai_client:
        return

    # 🌟 1. 10초 쿨다운 체크: 아직 10초가 안 지났으면 AI 호출 생략
    if time.time() < api_cooldown_until:
        return

    unknown_dests = []
    fast_match_keywords = ["BUSAN", "PUSAN", "KRBUS", "KRPUS", "KR BUS", "KR PUS"]
    negative_keywords = [
        "SHANGHAI", "SINGAPORE", "TOKYO", "OSAKA", "QINGDAO", "NINGBO",
        "HONG KONG", "HKG", "YOKOHAMA", "NAGOYA", "KOBE", "VLADIVOSTOK",
        "CN ", "JP ", "US ", "TW ", "VN "
    ]

    # 캐시나 키워드에 없는 "진짜 모르는 목적지"만 추려냄
    for dest in destinations:
        if not dest: continue
        dest_upper = dest.strip().upper()

        if dest_upper in busan_dest_cache:
            continue

        if any(k in dest_upper for k in fast_match_keywords):
            busan_dest_cache[dest_upper] = True
            continue

        if any(k in dest_upper for k in negative_keywords):
            busan_dest_cache[dest_upper] = False
            continue

        unknown_dests.append(dest_upper)

    # 모르는 목적지가 없으면 API 호출 없이 종료
    if not unknown_dests:
        return

    # 동시 다발적인 API 호출 방지
    async with api_semaphore:
        try:
            # 🌟 2. 호출 즉시 다음 호출 가능 시간을 '현재 시간 + 10초'로 설정
            # (프런트가 3초마다 요청해도 백엔드는 10초에 1번만 AI를 찌름)
            api_cooldown_until = time.time() + 10

            prompt = f"""다음은 선박 목적지 텍스트 목록입니다.
각 텍스트가 대한민국 '부산(Busan/Pusan)'을 의미하는지 판별해주세요.
반드시 아래와 같은 JSON 형식으로만 응답하세요. 마크다운 기호나 다른 설명은 절대 하지 마세요.
{{
  "목적지텍스트1": true,
  "목적지텍스트2": false
}}

목적지 목록:
{json.dumps(unknown_dests, ensure_ascii=False)}"""

            # 🌟 3. 정상 작동하던 gemini-2.0-flash 로 복구 (404 에러 해결)
            response = await ai_client.aio.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )

            result_text = response.text.replace("```json", "").replace("```", "").strip()
            parsed_result = json.loads(result_text)

            for k, v in parsed_result.items():
                busan_dest_cache[k.upper()] = bool(v)

            for dest in unknown_dests:
                if dest not in busan_dest_cache:
                    busan_dest_cache[dest] = False

        except Exception as e:
            error_msg = str(e)
            print(f"Batch AI Error: {error_msg}")

            # 429 에러가 혹시라도 발생하면 60초 대기
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                print("⚠️ API 한도 초과! 60초 동안 대기합니다.")
                api_cooldown_until = time.time() + 60


# ==========================================
# 7. FastAPI 앱 및 템플릿 설정
# ==========================================
app = FastAPI()
templates = Jinja2Templates(directory="templates")


# ==========================================
# 8. 라우터 (Endpoints)
# ==========================================
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


@app.get("/api/ships")
async def get_ships_api():
    async with AsyncSessionLocal() as session:
        stmt = select(StvAIS).order_by(StvAIS.regDate.desc()).limit(100)
        result = await session.execute(stmt)
        ships = result.scalars().all()

        # 🌟 1. 100개 선박 데이터에서 중복을 제거한 목적지 목록 추출
        unique_destinations = {ship.destination for ship in ships if ship.destination}

        # 🌟 2. 모르는 목적지들만 모아서 한 번에 AI에게 질문 (Batch 처리)
        await update_busan_cache_batch(unique_destinations)

        # 3. 결과 매핑 및 반환
        ship_list = []
        for ship in ships:
            dest_upper = ship.destination.strip().upper() if ship.destination else ""
            is_busan = busan_dest_cache.get(dest_upper, False)

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
                "attrib": ship.attrib,
                "isBusan": is_busan  # 캐시된 결과값 주입
            })
        return ship_list


@app.get("/api/vessels/{imo}", response_model=VesselResponse)
async def get_vessel_info(imo: str):
    if not imo.isdigit() or len(imo) != 7:
        raise HTTPException(status_code=400, detail="Invalid IMO number format")

    async with AsyncSessionLocal() as session:
        stmt = select(VesselMst).where(VesselMst.imoNo == imo)
        result = await session.execute(stmt)
        db_vessel = result.scalars().first()
        if db_vessel:
            response_data = VesselResponse.model_validate(db_vessel) if hasattr(VesselResponse,
                                                                                'model_validate') else VesselResponse.from_orm(
                db_vessel)
            response_data.source = "DB Cache"
            return response_data
        api_data = await fetch_vessel_from_api(imo)
        new_vessel = VesselMst(**api_data)
        session.add(new_vessel)
        await session.commit()
        await session.refresh(new_vessel)
        response_data = VesselResponse.model_validate(new_vessel) if hasattr(VesselResponse,
                                                                             'model_validate') else VesselResponse.from_orm(
            new_vessel)
        response_data.source = "VesselAPI (Newly Cached)"
        return response_data
