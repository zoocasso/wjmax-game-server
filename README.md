<div align="center">

# 🎹 WJMAX Game Server

**Production Backend for a Fan Rhythm Game — ~2,000 Peak Concurrent Players**

[![EN](https://img.shields.io/badge/Language-English-blue?style=flat-square)](#-english)
[![KR](https://img.shields.io/badge/언어-한국어-red?style=flat-square)](#-한국어)

</div>

---

## 🇺🇸 English

A production backend for **WJMAX**, a fan-made rhythm game in the Woowakgood community (side project, Aug 2023 – Feb 2024). The team was two people: the main developer built the game, and I joined at their request as the **sole server developer**, designing and operating the server, security layer, and database.

### 📋 Project Overview

Built and operated the backend through live service, including update-day traffic peaks. Responsibilities covered infrastructure design, a Cloudflare edge layer, and a play-log ingestion API.

- **Role:** Sole server developer — backend server, security, and database
- **Scale:** ~300 average and ~2,000 peak concurrent players (during updates)
- **Setup:** FastAPI on Docker (AWS EC2) with RDS MySQL, behind a Cloudflare proxy/WAF

### 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | FastAPI |
| **Container** | Docker |
| **Cloud & Infra** | AWS (EC2, RDS), Cloudflare |
| **Database** | MySQL (AWS RDS) |

### 🚀 Key Responsibilities

#### 1. Infrastructure Design & Deployment
- **AWS EC2 + Docker** — Containerized the FastAPI server to guarantee environment consistency and streamline deployment across dev and production.
- **AWS RDS (MySQL)** — Kept the database on managed RDS, separate from the application server.

#### 2. Security & Network
- **Cloudflare Edge Layer** — Put Cloudflare DNS and its WAF/proxy in front of the origin to hide the origin server and filter malicious traffic before it reached the application.

#### 3. Play-Log Collection
- Built an API that collects gameplay logs during live service, as a basis for later analysis and service monitoring.

### 🏗 System Architecture

> The repository contains the initial prototype code. The production deployment was structured as follows:
> **Client → Cloudflare (WAF + Proxy) → AWS EC2 (FastAPI on Docker) → AWS RDS (MySQL)**

1. **Traffic Entry** — Cloudflare (WAF & Proxy)
2. **Application Layer** — AWS EC2 running FastAPI inside Docker
3. **Data Layer** — AWS RDS (managed MySQL)

<div align="right"><a href="#-한국어">🇰🇷 한국어로 보기 ↓</a></div>

---

## 🇰🇷 한국어

우왁굳 팬게임 **'왁제이맥스(WJMAX)'**의 운영 백엔드입니다(개인 사이드 프로젝트, 2023.08 ~ 2024.02). 2인 팀으로, 게임은 메인 개발자가 만들고 저는 그 요청으로 합류해 **서버를 단독으로** 맡아 서버·보안 계층·데이터베이스를 설계하고 운영했습니다.

### 📋 프로젝트 개요

업데이트 날의 접속 피크를 포함해 라이브 서비스 기간 동안 백엔드를 구축·운영했습니다. 인프라 설계, Cloudflare 엣지 계층, 플레이 로그 수집 API를 담당했습니다.

- **역할:** 서버 단독 담당 — 백엔드 서버, 보안, 데이터베이스
- **규모:** 평균 동시 접속자 약 300명, 업데이트 시 최대 약 2,000명
- **구성:** AWS EC2의 FastAPI(Docker) + RDS MySQL, 앞단에 Cloudflare 프록시·WAF

### 🛠 기술 스택

| 계층 | 기술 |
|---|---|
| **프레임워크** | FastAPI |
| **컨테이너** | Docker |
| **클라우드/인프라** | AWS (EC2, RDS), Cloudflare |
| **데이터베이스** | MySQL (AWS RDS) |

### 🚀 주요 수행 업무

#### 1. 인프라 설계 및 배포
- **AWS EC2 + Docker** — FastAPI 서버를 컨테이너화하여 개발·운영 환경 간 일관성을 보장하고 배포 효율을 높였습니다.
- **AWS RDS (MySQL)** — 데이터베이스를 애플리케이션 서버와 분리해 관리형 RDS에 두었습니다.

#### 2. 보안 및 네트워크
- **Cloudflare 엣지 계층** — 오리진 앞단에 Cloudflare DNS와 WAF/프록시를 두어 오리진 서버를 감추고, 악성 트래픽이 애플리케이션에 닿기 전에 걸러냈습니다.

#### 3. 플레이 로그 수집
- 라이브 서비스 중 게임 플레이 로그를 수집하는 API를 만들어, 이후 분석과 서비스 모니터링의 기반을 마련했습니다.

### 🏗 시스템 아키텍처

> 본 리포지토리에는 초기 프로토타입 코드가 포함되어 있으며, 실제 운영 환경은 아래와 같이 구성되었습니다.
> **Client → Cloudflare (WAF + Proxy) → AWS EC2 (FastAPI on Docker) → AWS RDS (MySQL)**

1. **트래픽 진입** — Cloudflare (WAF & Proxy)
2. **애플리케이션 계층** — AWS EC2에서 Docker 기반 FastAPI 구동
3. **데이터 계층** — AWS RDS (Managed MySQL)

<div align="right"><a href="#-english">🇺🇸 View in English ↑</a></div>
