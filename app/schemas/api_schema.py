from decimal import Decimal

from pydantic import BaseModel, Field


class PlanSaveRequest(BaseModel):
    purpose: str
    strain: str | None = None
    batch1: str | None = None
    batch2: str | None = None
    batch3: str | None = None
    batch4: str | None = None
    cmp: str | None = None
    result: str | None = None


class BatchParams(BaseModel):
    prepTime: Decimal | None = None
    equipVol: Decimal | None = None
    purifyYield: Decimal | None = None
    dcwOdFactor: Decimal | None = None
    feedGlucoseConc: Decimal | None = None
    feedDensity: Decimal | None = None
    feedGlucosePerFeed: Decimal | None = None


class BatchComparison(BaseModel):
    type: str | None = None
    targetBatchId: str | None = None


class BatchResearcherRequest(BaseModel):
    role: str
    id: str


class SamplingRow(BaseModel):
    samplingTime: Decimal
    od: Decimal | None = None
    feedWeight: Decimal | None = None
    brothVolume: Decimal | None = None
    targetProdConc: Decimal | None = None
    glucoseConc: Decimal | None = None
    lycopene: Decimal | None = None
    aCarotene: Decimal | None = None
    bCarotene: Decimal | None = None
    citricAcid: Decimal | None = None
    pyruvicAcid: Decimal | None = None
    succinicAcid: Decimal | None = None
    lacticAcid: Decimal | None = None
    aceticAcid: Decimal | None = None


class BatchDetailSaveRequest(BaseModel):
    startDt: str | None = None
    params: BatchParams = Field(default_factory=BatchParams)
    comparison: BatchComparison = Field(default_factory=BatchComparison)
    researchers: list[BatchResearcherRequest] = Field(default_factory=list)
    samplingRows: list[SamplingRow] = Field(default_factory=list)


class SamplingSaveRequest(BaseModel):
    rows: list[SamplingRow] = Field(default_factory=list)


class BestBatchCreateRequest(BaseModel):
    batch_id: str
    reg_id: str | None = None


class CompareBatchSaveRequest(BaseModel):
    cmp_batch_id: str
    upd_id: str | None = None


class CalculationRunRequest(BaseModel):
    recalculate: bool = True
    reg_id: str | None = None


class CalcSampleSaveRequest(BaseModel):
    sample_id: int
    upd_id: str | None = None
