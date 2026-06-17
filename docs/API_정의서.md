# Sillicobio LIMS — API 목록 v3

> 기준: PostgreSQL 테이블 정의서 v5 / 생성 SQL v1  
> Base URL: `/api/v1`  
> 기본 요청/응답: `Content-Type: application/json`  
> 파일 업로드: `multipart/form-data`  
> 파일 다운로드: 바이너리 응답 + `Content-Disposition: attachment`  
> 인증 방식: **토큰 인증 미사용 / DB 평문 비밀번호 비교 + 서버 세션 방식**

---

## 0. v3 개정 요약

| 구분 | 변경 내용 |
|---|---|
| 인증 | JWT/Bearer Token 제거 |
| 로그인 | `tb_member.member_id`, `tb_member.password` 평문 비교 |
| 세션 | 로그인 성공 시 서버 세션 생성, 브라우저는 세션 쿠키 사용 |
| Authorization Header | 사용하지 않음 |
| 회원 | `org`, `dept`, `email`, `tel` 제거 |
| 회원 로그 | `last_login_dt`, `last_login_ip`는 DB 로그성 필드로 갱신 |
| 연구자 | `email`, `tel` 유지 |
| 연구자 | `org`, `dept` 제거 |
| 실험계획 | `start` 제거, 실험 시작일은 배치의 `startDt` 기준 |
| 명칭 | 산출전체 / 산출요약 기준 유지 |
| 로그성 정보 | 화면 조회 API 없이 DB에 자동 저장 |
| 산출 비교 | 전체 DB 검색이 아니라 배치정보에서 선택된 비교배치의 샘플링 데이터만 비교 대상으로 사용 |

---

## 1. 공통 정책

### 1.1 인증 방식

본 시스템은 JWT, Bearer Token 등의 토큰 인증 방식을 사용하지 않습니다.

로그인은 `tb_member` 테이블의 `member_id`, `password`를 직접 비교하는 방식으로 처리합니다. 비밀번호는 내부 업무용 시스템 정책에 따라 평문 저장하며, 로그인 시에도 평문 비교합니다.

로그인 성공 시 서버는 세션을 생성하고, 브라우저에는 세션 쿠키를 발급합니다. 이후 API 요청은 브라우저가 자동으로 전송하는 세션 쿠키를 통해 로그인 여부와 권한을 확인합니다.

```http
Authorization: 사용하지 않음
Cookie: SESSION=<server-session-id>
```

프론트엔드에서 `fetch` 또는 `axios`를 사용할 경우 쿠키가 전달되도록 아래 설정이 필요합니다.

```ts
// fetch
fetch("/api/v1/auth/me", {
  credentials: "include"
});

// axios
axios.defaults.withCredentials = true;
```

### 1.2 로그인 처리 정책

| 단계 | 처리 내용 |
|---|---|
| 1 | 사용자가 ID / 비밀번호 입력 |
| 2 | 서버에서 `tb_member.member_id` 조회 |
| 3 | 입력 비밀번호와 `tb_member.password` 평문 비교 |
| 4 | 일치하면 로그인 성공 |
| 5 | `last_login_dt`, `last_login_ip` 갱신 |
| 6 | 서버 세션 생성 |
| 7 | 세션 쿠키 발급 |
| 8 | 사용자 정보 반환 |

### 1.3 권한 정책

| 권한 | 접근 가능 메뉴 | 등록/수정 권한 |
|---|---|---|
| 관리자 | 실험계획, 배치정보, 결과정보, 연구자정보, 회원정보 | 전체 등록/수정 가능 |
| 사용자 | 실험계획, 배치정보, 결과정보 | 연구자정보/회원정보 접근 불가 |

정책:

- 사용자 권한은 프론트에서 `연구자정보`, `회원정보` 메뉴를 숨깁니다.
- 사용자 권한이 `/researchers`, `/members` API에 접근하면 서버는 `403 Forbidden`을 반환합니다.
- 로그성 정보는 화면에 표시하지 않고 서버에서 DB에만 자동 생성합니다.

### 1.4 목록 정렬 정책

목록을 반환하는 API의 기본 정렬 방향은 내림차순입니다.

정책:

- 별도 정렬 파라미터가 없는 목록 API는 최신 등록 데이터 또는 큰 식별자가 먼저 오도록 반환합니다.
- 정렬 파라미터가 있는 API도 기본값은 `desc`입니다.
- 프론트에서 명시적으로 `asc`를 요청한 경우에만 오름차순으로 반환합니다.

### 1.5 날짜 형식

| 용도 | 형식 | 예시 |
|---|---|---|
| API 저장/응답 | `YYYYMMDD` | `20260610` |
| 화면 표시 | `YYYY.MM.DD` | `2026.06.10` |
| 로그/일시 | ISO 또는 `YYYYMMDDHHmmss` | `20260610120000` |

### 1.6 페이지네이션

```json
{
  "total": 100,
  "page": 1,
  "size": 10,
  "items": []
}
```

### 1.7 에러 응답

```json
{
  "code": "VALIDATION_ERROR",
  "message": "필수값이 누락되었습니다.",
  "details": [
    {
      "field": "name",
      "reason": "연구자 이름은 필수입니다."
    }
  ]
}
```

| HTTP 코드 | 설명 |
|---|---|
| `400` | 잘못된 요청, 필수값 누락, 형식 오류 |
| `401` | 세션 없음 또는 로그인 만료 |
| `403` | 권한 없음 |
| `404` | 리소스 없음 |
| `409` | 중복 또는 충돌 |
| `500` | 서버 오류 |

### 1.8 Audit Log 정책

1차 개발 범위에서는 로그 조회 화면/API를 제공하지 않습니다.

프론트엔드가 별도로 호출해야 하는 Audit Log API도 제공하지 않습니다. 서버가 API 요청 성공 후 `tb_audit_log`에 자동 저장합니다.

서버는 아래 이벤트 발생 시 DB에 로그를 자동 생성합니다.

- 로그인
- 로그아웃
- 실험계획 등록/수정
- 배치정보 수정
- 샘플링 데이터 저장
- 연구자 등록/수정
- 회원 등록/수정
- 파일 업로드/다운로드
- 산출 확인 화면 조회

권장 로그 구조:

```json
{
  "id": 1,
  "actorId": "user01",
  "action": "BATCH_UPDATE",
  "resourceType": "BATCH",
  "resourceId": "LAB00001_BAT01",
  "ip": "127.0.0.1",
  "createdAt": "20260610120000"
}
```

현재 자동 저장 필드:

| DB 컬럼 | 내용 |
| --- | --- |
| `action_type` | `LOGIN`, `LOGOUT`, `CREATE`, `UPDATE`, `DELETE`, `UPLOAD`, `DOWNLOAD`, `CALC_VIEW` |
| `target_table` | 대상 테이블명 |
| `target_id` | 대상 ID. 경로에서 확인 가능한 경우 저장 |
| `request_method` | HTTP method |
| `request_path` | 요청 path |
| `client_ip` | 클라이언트 IP |
| `user_agent` | 브라우저 user-agent |
| `reg_id` | 요청 사용자 ID |
| `reg_dt` | 로그 생성 시각 |

---

## 2. 인증 Auth

### 2.1 로그인

`POST /auth/login`

**Request**

```json
{
  "id": "user01",
  "password": "1234"
}
```

**처리 방식**

1. `tb_member.member_id = id` 조회
2. `tb_member.password`와 입력 비밀번호 평문 비교
3. 권한 `role_cd` 확인
4. `last_login_dt`, `last_login_ip` 갱신
5. 서버 세션 생성
6. 세션 쿠키 발급
7. 사용자 정보 반환

**Response** `200 OK`

```http
Set-Cookie: SESSION=<server-session-id>; HttpOnly; Path=/; SameSite=Lax
```

```json
{
  "id": "user01",
  "name": "일반사용자",
  "role": "USER"
}
```

**실패 응답 예시**

```json
{
  "code": "LOGIN_FAILED",
  "message": "ID 또는 비밀번호가 올바르지 않습니다."
}
```

### 2.2 현재 사용자 조회

`GET /auth/me`

새로고침 또는 팝업 진입 시 현재 로그인 사용자와 권한을 확인하기 위한 API입니다. 세션 쿠키 기준으로 로그인 상태를 확인합니다.

**Response** `200 OK`

```json
{
  "id": "user01",
  "name": "일반사용자",
  "role": "USER"
}
```

세션이 없거나 만료된 경우:

```json
{
  "code": "UNAUTHORIZED",
  "message": "로그인이 필요합니다."
}
```

### 2.3 로그아웃

`POST /auth/logout`

서버 세션을 삭제하고 세션 쿠키를 만료합니다.

**Response** `204 No Content`

---

## 3. 연구자 Researcher

### 3.1 연구자 목록 조회

`GET /researchers`

관리자 전용 API입니다.

**Query Parameters**

| 파라미터 | 타입 | 설명 |
|---|---|---|
| `id` | string | 연구자 ID 검색, 부분 일치 |
| `name` | string | 연구자명 검색, 부분 일치 |
| `page` | number | 페이지 번호, 기본값 1 |
| `size` | number | 페이지 크기, 기본값 10 |

**Response** `200 OK`

```json
{
  "total": 2,
  "page": 1,
  "size": 10,
  "items": [
    {
      "id": "RES001",
      "name": "김민준",
      "email": "minjun.kim@sillicobio.local",
      "tel": "010-1001-1001"
    }
  ]
}
```

### 3.2 연구자 등록

`POST /researchers`

관리자 전용 API입니다. 연구자 ID는 서버에서 `RES001` 형식으로 자동 생성하거나, 관리자 입력값을 검증 후 저장합니다.

**Request**

```json
{
  "name": "김민준",
  "email": "minjun.kim@sillicobio.local",
  "tel": "010-1001-1001"
}
```

**Response** `201 Created`

```json
{
  "id": "RES001",
  "name": "김민준",
  "email": "minjun.kim@sillicobio.local",
  "tel": "010-1001-1001"
}
```

### 3.3 연구자 수정

`PUT /researchers/{id}`

관리자 전용 API입니다.

**Request**

```json
{
  "name": "김민준",
  "email": "minjun.kim@sillicobio.local",
  "tel": "010-1001-1001"
}
```

**Response** `200 OK` — 수정된 연구자 객체

### 3.4 연구자 유효성

| 항목 | 규칙 |
|---|---|
| `id` | `RES001` 형식 |
| `name` | 필수 |
| `email` | 선택값, 입력 시 이메일 형식 권장 |
| `tel` | 선택값 |

---

## 4. 회원 Member

### 4.1 회원 목록 조회

`GET /members`

관리자 전용 API입니다.

**Query Parameters**

| 파라미터 | 타입 | 설명 |
|---|---|---|
| `id` | string | 회원 ID 검색, 부분 일치 |
| `name` | string | 회원명 검색, 부분 일치 |
| `page` | number | 페이지 번호, 기본값 1 |
| `size` | number | 페이지 크기, 기본값 10 |

**Response** `200 OK`

> 현재 요구사항 기준으로 패스워드는 암호화하지 않고 목록에 노출합니다. 내부망 운영 전제의 정책입니다. `lastLoginAt`, `lastLoginIp`는 로그성 정보이므로 기본 회원 목록 화면에는 노출하지 않습니다.

```json
{
  "total": 2,
  "page": 1,
  "size": 10,
  "items": [
    {
      "id": "admin",
      "name": "관리자",
      "password": "1234",
      "role": "ADMIN",
      "created": "20260610"
    }
  ]
}
```

### 4.2 회원 등록

`POST /members`

관리자 전용 API입니다. 관리자 계정도 이 API로 추가할 수 있습니다.

**Request**

```json
{
  "id": "user01",
  "name": "일반사용자",
  "password": "1234",
  "role": "USER"
}
```

**Response** `201 Created`

```json
{
  "id": "user01",
  "name": "일반사용자",
  "password": "1234",
  "role": "USER",
  "created": "20260610"
}
```

### 4.3 회원 수정

`PUT /members/{id}`

관리자 전용 API입니다.

**Request**

```json
{
  "name": "일반사용자",
  "password": "1234",
  "role": "USER"
}
```

**Response** `200 OK` — 수정된 회원 객체

### 4.4 회원 유효성

| 항목 | 규칙 |
|---|---|
| `id` | 필수, 중복 불가 |
| `name` | 필수 |
| `password` | 필수, 평문 저장/노출 |
| `role` | `ADMIN` 또는 `USER` |
| `created` | 서버에서 자동 생성 |

---

## 5. 실험계획 Plan

### 5.1 실험계획 목록 조회

`GET /plans`

**Query Parameters**

| 파라미터 | 타입 | 설명 |
|---|---|---|
| `id` | string | 실험 ID 검색, 부분 일치 |
| `purpose` | string | 실험목적 검색, 부분 일치 |
| `createdFrom` | string | 생성일 시작, `YYYYMMDD` |
| `createdTo` | string | 생성일 종료, `YYYYMMDD` |
| `sort` | string | 기본값 `created,desc` |
| `page` | number | 페이지 번호, 기본값 1 |
| `size` | number | 페이지 크기, 기본값 10 |

**Response** `200 OK`

```json
{
  "total": 1,
  "page": 1,
  "size": 10,
  "items": [
    {
      "id": "LAB00001",
      "purpose": "Lutein 생산성 향상을 위한 배양 조건 비교 실험",
      "strain": "Saccharomyces cerevisiae SB-LUT-01",
      "batch1": "배치 1호: 기본 배양 조건으로 대조군 운전",
      "batch2": "배치 2호: Feed glucose 농도 상향 조건 운전",
      "batch3": "배치 3호: 접종비 변경 조건 운전",
      "batch4": "배치 4호: 배양 온도 및 교반 조건 최적화 운전",
      "result": "테스트용 실험계획 데이터입니다.",
      "cmp": null,
      "planFile": null,
      "allFile": null,
      "created": "20260610"
    }
  ]
}
```

### 5.2 실험계획 단건 조회

`GET /plans/{id}`

실험계획 상세 보기용 API입니다.

**Response** `200 OK` — Plan 객체 단건

### 5.3 실험계획 등록

`POST /plans`

등록 시 서버에서 실험 ID를 `LAB00001` 형식으로 자동 생성하고, 배치 4개를 자동 생성합니다.

**Request**

```json
{
  "purpose": "Lutein 생산성 향상을 위한 배양 조건 비교 실험",
  "strain": "Saccharomyces cerevisiae SB-LUT-01",
  "batch1": "배치 1호: 기본 배양 조건으로 대조군 운전",
  "batch2": "배치 2호: Feed glucose 농도 상향 조건 운전",
  "batch3": "배치 3호: 접종비 변경 조건 운전",
  "batch4": "배치 4호: 배양 온도 및 교반 조건 최적화 운전",
  "cmp": null,
  "result": "테스트용 실험계획 데이터입니다."
}
```

**Response** `201 Created`

```json
{
  "plan": {
    "id": "LAB00001",
    "purpose": "Lutein 생산성 향상을 위한 배양 조건 비교 실험",
    "strain": "Saccharomyces cerevisiae SB-LUT-01",
    "batch1": "배치 1호: 기본 배양 조건으로 대조군 운전",
    "batch2": "배치 2호: Feed glucose 농도 상향 조건 운전",
    "batch3": "배치 3호: 접종비 변경 조건 운전",
    "batch4": "배치 4호: 배양 온도 및 교반 조건 최적화 운전",
    "cmp": null,
    "result": "테스트용 실험계획 데이터입니다.",
    "created": "20260610"
  },
  "batches": [
    { "id": "LAB00001_BAT01", "planId": "LAB00001" },
    { "id": "LAB00001_BAT02", "planId": "LAB00001" },
    { "id": "LAB00001_BAT03", "planId": "LAB00001" },
    { "id": "LAB00001_BAT04", "planId": "LAB00001" }
  ]
}
```

### 5.4 실험계획 수정

`PUT /plans/{id}`

**Request**

```json
{
  "purpose": "Lutein 생산성 향상을 위한 배양 조건 비교 실험",
  "strain": "Saccharomyces cerevisiae SB-LUT-01",
  "batch1": "배치 1호: 기본 배양 조건으로 대조군 운전",
  "batch2": "배치 2호: Feed glucose 농도 상향 조건 운전",
  "batch3": "배치 3호: 접종비 변경 조건 운전",
  "batch4": "배치 4호: 배양 온도 및 교반 조건 최적화 운전",
  "cmp": null,
  "result": "테스트용 실험계획 데이터입니다."
}
```

**Response** `200 OK` — 수정된 Plan 객체

### 5.5 실험계획 파일 업로드

`POST /plans/{id}/files`

**Form Data**

| 필드 | 설명 |
|---|---|
| `fileType` | `PLAN` 또는 `ALL` |
| `file` | 업로드 파일 |

**Response** `201 Created`

```json
{
  "fileId": 1,
  "fileType": "PLAN",
  "fileName": "실험계획서.pdf",
  "fileSize": 102400,
  "mimeType": "application/pdf"
}
```

---

## 6. 배치정보 Batch

### 6.1 배치 목록 조회

`GET /batches`

**Query Parameters**

| 파라미터 | 타입 | 설명 |
|---|---|---|
| `planId` | string | 실험 ID |
| `batchId` | string | 배치 ID |
| `purpose` | string | 실험목적 검색 |
| `sort` | string | 기본값 `created,desc`. `created`, `batchId`, `planId`, `purpose` 기준 정렬 가능 |
| `page` | number | 페이지 번호 |
| `size` | number | 페이지 크기 |

**Response** `200 OK`

```json
{
  "total": 4,
  "page": 1,
  "size": 10,
  "items": [
    {
      "planId": "LAB00001",
      "purpose": "Lutein 생산성 향상을 위한 배양 조건 비교 실험",
      "batchId": "LAB00001_BAT01",
      "created": "20260610"
    }
  ]
}
```

### 6.2 배치 단건 조회

`GET /batches/{batchId}`

**Response** `200 OK`

```json
{
  "batchId": "LAB00001_BAT01",
  "planId": "LAB00001",
  "purpose": "Lutein 생산성 향상을 위한 배양 조건 비교 실험",
  "startDt": "20260610",
  "params": {
    "prepTime": 24,
    "equipVol": 5,
    "purifyYield": 0.85,
    "dcwOdFactor": 0.31,
    "feedGlucoseConc": 600,
    "feedDensity": 1.2,
    "feedGlucosePerFeed": 0.5
  },
  "comparison": {
    "type": "ALL",
    "targetBatchId": "LAB00001_BAT01"
  },
  "researchers": [
    { "role": "RES1", "id": "RES001", "name": "김민준" }
  ],
  "files": {
    "doPh": null,
    "co2O2": null,
    "ref": null
  }
}
```

### 6.3 배치 상세 저장

`PUT /batches/{batchId}/detail`

배치 기본내용, 비교배치, 참여연구원을 저장합니다.

샘플링 데이터는 이 API에서 저장하지 않습니다. 샘플링 변경은 `PUT /batches/{batchId}/sampling`을 사용합니다.

**Request**

```json
{
  "startDt": "20260610",
  "params": {
    "prepTime": 24,
    "equipVol": 5,
    "purifyYield": 0.85,
    "dcwOdFactor": 0.31,
    "feedGlucoseConc": 600,
    "feedDensity": 1.2
  },
  "comparison": {
    "type": "ALL",
    "targetBatchId": null
  },
  "researchers": [
    { "role": "RES1", "id": "RES001" },
    { "role": "RES2", "id": "RES002" }
  ],
  "samplingRows": []
}
```

`samplingRows`는 하위 호환을 위해 요청 스키마에 남아 있지만, 상세 저장 API에서는 처리하지 않습니다.

**Response** `200 OK`

```json
{
  "batchId": "LAB00001_BAT01",
  "message": "배치정보가 저장되었습니다."
}
```

### 6.4 비교배치 선택 옵션

`GET /batches/options`

**Query Parameters**

| 파라미터 | 타입 | 설명 |
|---|---|---|
| `excludeBatchId` | string | 현재 배치 제외 |
| `keyword` | string | 배치 ID 또는 실험목적 검색 |

**Response** `200 OK`

```json
{
  "items": [
    {
      "batchId": "LAB00001_BAT01",
      "planId": "LAB00001",
      "purpose": "Lutein 생산성 향상을 위한 배양 조건 비교 실험"
    }
  ]
}
```

### 6.5 비교배치 저장

`PUT /batches/{batchId}/compare-batch`

배치정보 화면에서 선택한 비교배치를 저장합니다.

**Request**

```json
{
  "cmp_batch_id": "LAB00001_BAT02"
}
```

**Response** `200 OK`

```json
{
  "message": "비교배치가 저장되었습니다.",
  "batch": {
    "batch_id": "LAB00001_BAT01",
    "cmp_type": "BATCH",
    "cmp_batch_id": "LAB00001_BAT02"
  }
}
```

정책:

- 자기 자신은 비교배치로 저장할 수 없습니다. 이 경우 `400 Bad Request`를 반환합니다.
- 산출 비교 로직은 `tb_batch.cmp_batch_id`에 저장된 비교배치만 사용합니다.
- 선택된 비교배치에 샘플링 데이터가 없으면 비교 관련 값은 `null`로 반환됩니다.

### 6.6 비교배치 조회

`GET /batches/{batchId}/compare-batch`

**Response** `200 OK`

```json
{
  "batch_id": "LAB00001_BAT01",
  "cmp_type": "BATCH",
  "cmp_batch_id": "LAB00001_BAT02",
  "cmp_batch_name": "LAB00001_BAT02"
}
```

### 6.7 배치 파일 업로드

`POST /batches/{batchId}/files`

**Form Data**

| 필드 | 설명 |
|---|---|
| `fileType` | `DO_PH`, `CO2_O2`, `REF`, `TREND_CSV` |
| `file` | 업로드 파일 |

**Response** `201 Created`

```json
{
  "fileId": 10,
  "fileType": "DO_PH",
  "fileName": "do_ph.csv",
  "fileSize": 204800,
  "mimeType": "text/csv"
}
```

---

## 7. 샘플링 Sampling

### 7.1 샘플링 조회

`GET /batches/{batchId}/sampling`

**Response** `200 OK`

```json
{
  "batchId": "LAB00001_BAT01",
  "columns": [
    "samplingTime",
    "od",
    "feedWeight",
    "brothVolume",
    "targetProdConc",
    "glucoseConc",
    "lycopene",
    "aCarotene",
    "bCarotene",
    "citricAcid",
    "pyruvicAcid",
    "succinicAcid",
    "lacticAcid",
    "aceticAcid"
  ],
  "rows": [
    {
      "samplingTime": 0,
      "od": 0.2,
      "feedWeight": 0,
      "brothVolume": 5,
      "targetProdConc": 0,
      "glucoseConc": 20,
      "lycopene": 0,
      "aCarotene": 0,
      "bCarotene": 0,
      "citricAcid": 0,
      "pyruvicAcid": 0,
      "succinicAcid": 0,
      "lacticAcid": 0,
      "aceticAcid": 0
    }
  ]
}
```

### 7.2 샘플링 저장

`PUT /batches/{batchId}/sampling`

저장 후 산출전체/산출요약을 재계산합니다.

**Request**

```json
{
  "rows": [
    {
      "samplingTime": 0,
      "od": 0.2,
      "feedWeight": 0,
      "brothVolume": 5,
      "targetProdConc": 0,
      "glucoseConc": 20,
      "lycopene": 0,
      "aCarotene": 0,
      "bCarotene": 0,
      "citricAcid": 0,
      "pyruvicAcid": 0,
      "succinicAcid": 0,
      "lacticAcid": 0,
      "aceticAcid": 0
    }
  ]
}
```

**Response** `200 OK`

```json
{
  "batchId": "LAB00001_BAT01",
  "message": "샘플링 데이터가 저장되었습니다.",
  "recalculated": true
}
```

---

## 8. 산출 Calculation

### 8.1 산출확인 기준 샘플 저장

`PUT /batches/{batchId}/calc-sample`

산출 확인 팝업에서 기준 샘플링 row를 선택할 때 호출합니다.

**Request**

```json
{
  "sample_id": 123
}
```

**Response** `200 OK`

```json
{
  "message": "산출확인 기준 샘플링 데이터가 저장되었습니다.",
  "batch_id": "LAB00001_BAT01",
  "calc_sample_id": 123,
  "calcSample": {
    "id": 123,
    "isCalcSample": true,
    "samplingTime": 72,
    "od": 7.2,
    "feedWeight": 37.5,
    "brothVolume": 3.8,
    "targetProdConc": 2.3,
    "glucoseConc": 3.1
  }
}
```

정책:

- `sample_id`는 현재 `batchId`에 속한 샘플링 row여야 합니다.
- 다른 배치의 샘플링 row를 지정하면 `400 Bad Request`를 반환합니다.

### 8.2 산출확인 기준 샘플 조회

`GET /batches/{batchId}/calc-sample`

**Response** `200 OK`

```json
{
  "batchId": "LAB00001_BAT01",
  "calcSampleId": 123,
  "hasCalcSample": true,
  "calcSample": {
    "id": 123,
    "isCalcSample": true,
    "samplingTime": 72,
    "od": 7.2,
    "feedWeight": 37.5,
    "brothVolume": 3.8,
    "targetProdConc": 2.3,
    "glucoseConc": 3.1
  }
}
```

### 8.3 산출 계산 가능 상태 조회

`GET /batches/{batchId}/calculation/status`

산출 확인 버튼 활성화 또는 클릭 직전 검증에 사용합니다.

**Response** `200 OK`

```json
{
  "batch_id": "LAB00001_BAT01",
  "has_batch": true,
  "saved_sampling_count": 5,
  "has_saved_sampling": true,
  "calc_sample_id": 123,
  "has_calc_sample": true,
  "compare_batch_id": "LAB00001_BAT02",
  "has_compare_batch": true,
  "can_calculate": true,
  "messages": []
}
```

### 8.4 산출 계산 실행

`POST /batches/{batchId}/calculation/run`

산출전체와 산출요약을 계산하고 DB에 저장한 뒤 결과를 반환합니다.

**Request**

```json
{
  "recalculate": true
}
```

**Response** `200 OK`

```json
{
  "message": "산출 계산이 완료되었습니다.",
  "batch_id": "LAB00001_BAT01",
  "compare_batch_id": "LAB00001_BAT02",
  "calc_sample_id": 123,
  "calculated_at": "2026-06-17T11:30:00",
  "full": [
    {
      "sample_id": 101,
      "sampling_time": 24,
      "base_sampling_time": 24,
      "yield_pct": 28,
      "productivity": 0.94,
      "abs_yield_up": 1.03,
      "prod_up": 0.98,
      "compare_batch_id": "LAB00001_BAT02",
      "compare_sample_id": 201,
      "compare_age": 23.5,
      "compare_sampling_time": 23.5,
      "compare_time_diff": 0.5,
      "matched_batch_id": "LAB00001_BAT02",
      "matched_sample_id": 201,
      "matched_sampling_time": 23.5
    }
  ],
  "summary": {}
}
```

#### 산출전체 비교배치 매칭 기준

- 전체 DB 또는 다른 배치의 샘플링 데이터는 비교 후보로 조회하지 않습니다.
- 배치정보에서 선택되어 `tb_batch.cmp_batch_id`에 저장된 비교배치의 샘플링 데이터만 비교 대상으로 사용합니다.
- 기준 배치의 각 산출전체 row는 자신의 `sampling_time` 또는 `age` 기준 ±1시간 안에 있는 비교배치 샘플링 row를 찾습니다.
- ±1시간 후보가 여러 개면 시간 차이가 가장 작은 row를 사용합니다. 시간 차이가 같으면 더 이른 `sampling_time`, 그 다음 작은 `sample_id`를 우선합니다.
- 마지막 산출전체 row는 시간 차이와 상관없이 비교배치 샘플링 데이터의 마지막 row와 반드시 비교합니다.
- 마지막 row가 아닌 row에서 ±1시간 후보가 없으면 `compare_sample_id`, `compare_sampling_time`, `compare_time_diff`, `abs_yield_up`, `prod_up` 등 비교 관련 값은 `null`입니다.
- 비교배치가 선택되지 않았거나 비교배치에 샘플링 데이터가 없으면 모든 산출전체 row의 비교 관련 값은 `null`입니다.

### 8.5 저장된 산출 계산 결과 조회

`GET /batches/{batchId}/calculation`

이미 DB에 저장된 산출 계산 결과를 조회합니다. 재계산하지 않습니다.

**Query Parameters**

| 파라미터 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `include_full` | boolean | `true` | 산출전체 포함 여부 |
| `include_summary` | boolean | `true` | 산출요약 포함 여부 |

응답 구조는 `POST /batches/{batchId}/calculation/run`과 동일합니다.

### 8.6 기존 산출 결과 조회

`GET /batches/{batchId}/calc`

배치별 저장 산출전체와 산출요약을 조회하는 기존 호환 API입니다.

**Response** `200 OK`

```json
{
  "batchId": "LAB00001_BAT01",
  "full": [],
  "summary": {}
}
```

### 8.7 산출 확인 원페이지 조회

`GET /batches/{batchId}/calc-view`

`window.open()` 팝업 화면에서 단독으로 호출 가능한 통합 조회 API입니다. 부모 화면의 React state나 localStorage에 의존하지 않고, URL의 `batchId`만으로 모든 데이터를 조회할 수 있어야 합니다.

**Response** `200 OK`

```json
{
  "batch": {},
  "plan": {},
  "researchers": [],
  "files": {},
  "sampling": [],
  "calcFull": [],
  "calcSummary": {}
}
```

---

## 9. 결과정보 Result

결과정보 화면은 별도의 결과 등록 테이블을 사용하지 않습니다.  
기존 배치정보, 샘플링, 산출전체, 산출요약 데이터를 조회하는 화면입니다.

### 9.1 결과정보 목록 조회

`GET /results`

**Query Parameters**

| 파라미터 | 타입 | 설명 |
|---|---|---|
| `planId` | string | 실험 ID |
| `batchId` | string | 배치 ID |
| `purpose` | string | 실험목적 검색 |
| `sort` | string | 기본값 `created,desc`. `created`, `batchId`, `planId`, `purpose`, `startDt` 기준 정렬 가능 |
| `page` | number | 페이지 번호 |
| `size` | number | 페이지 크기 |

**Response** `200 OK`

```json
{
  "total": 4,
  "page": 1,
  "size": 10,
  "items": [
    {
      "planId": "LAB00001",
      "batchId": "LAB00001_BAT01",
      "purpose": "Lutein 생산성 향상을 위한 배양 조건 비교 실험",
      "startDt": "20260610",
      "created": "20260610"
    }
  ]
}
```

### 9.2 결과정보 상세 조회

`GET /results/{batchId}`

내부적으로 `/batches/{batchId}/calc-view`와 동일한 데이터를 반환해도 됩니다.

---

## 10. 파일 다운로드

### 10.1 실험 파일 다운로드

`GET /plans/{id}/files/{fileId}`

### 10.2 배치 파일 다운로드

`GET /batches/{batchId}/files/{fileId}`

파일 다운로드 시 서버는 파일 존재 여부와 권한을 확인한 뒤 바이너리로 응답합니다.

---

## 11. 엑셀 다운로드

엑셀 다운로드는 현재 1차 개발 범위에서 보류합니다.  
따라서 아래 API는 문서상 보류 상태로만 관리합니다.

| API | 상태 |
|---|---|
| `GET /batches/export` | 보류 |
| `GET /batches/{batchId}/sampling/export` | 보류 |
| `GET /batches/{batchId}/calc/export` | 보류 |

---

## 12. API 요약

| 구분 | Method | URL | 설명 | 권한 |
|---|---|---|---|---|
| Auth | POST | `/auth/login` | 로그인, 세션 생성 | 전체 |
| Auth | GET | `/auth/me` | 현재 사용자 조회 | 로그인 |
| Auth | POST | `/auth/logout` | 로그아웃, 세션 삭제 | 로그인 |
| Researcher | GET | `/researchers` | 연구자 목록 | 관리자 |
| Researcher | POST | `/researchers` | 연구자 등록 | 관리자 |
| Researcher | PUT | `/researchers/{id}` | 연구자 수정 | 관리자 |
| Member | GET | `/members` | 회원 목록 | 관리자 |
| Member | POST | `/members` | 회원 등록 | 관리자 |
| Member | PUT | `/members/{id}` | 회원 수정 | 관리자 |
| Plan | GET | `/plans` | 실험계획 목록 | 로그인 |
| Plan | GET | `/plans/{id}` | 실험계획 상세 | 로그인 |
| Plan | POST | `/plans` | 실험계획 등록 | 로그인 |
| Plan | PUT | `/plans/{id}` | 실험계획 수정 | 로그인 |
| Plan | POST | `/plans/{id}/files` | 실험 파일 업로드 | 로그인 |
| Batch | GET | `/batches` | 배치 목록 | 로그인 |
| Batch | GET | `/batches/{batchId}` | 배치 상세 | 로그인 |
| Batch | PUT | `/batches/{batchId}/detail` | 배치 상세 저장 | 로그인 |
| Batch | GET | `/batches/options` | 비교배치 옵션 | 로그인 |
| Batch | PUT | `/batches/{batchId}/compare-batch` | 비교배치 저장 | 로그인 |
| Batch | GET | `/batches/{batchId}/compare-batch` | 비교배치 조회 | 로그인 |
| Batch | POST | `/batches/{batchId}/files` | 배치 파일 업로드 | 로그인 |
| Sampling | GET | `/batches/{batchId}/sampling` | 샘플링 조회 | 로그인 |
| Sampling | PUT | `/batches/{batchId}/sampling` | 샘플링 저장 | 로그인 |
| Calculation | PUT | `/batches/{batchId}/calc-sample` | 산출확인 기준 샘플 저장 | 로그인 |
| Calculation | GET | `/batches/{batchId}/calc-sample` | 산출확인 기준 샘플 조회 | 로그인 |
| Calculation | GET | `/batches/{batchId}/calculation/status` | 산출 계산 가능 상태 조회 | 로그인 |
| Calculation | POST | `/batches/{batchId}/calculation/run` | 산출 계산 실행 | 로그인 |
| Calculation | GET | `/batches/{batchId}/calculation` | 저장된 산출 계산 결과 조회 | 로그인 |
| Calculation | GET | `/batches/{batchId}/calc` | 기존 산출 결과 조회 | 로그인 |
| Calculation | GET | `/batches/{batchId}/calc-view` | 산출 확인 원페이지 조회 | 로그인 |
| Result | GET | `/results` | 결과정보 목록 | 로그인 |
| Result | GET | `/results/{batchId}` | 결과정보 상세 | 로그인 |
