<div align="center">

# 🎹 WJMAX Game Server

**High-Availability Backend for a Fan Rhythm Game — 3K Peak Concurrent Users**

[![EN](https://img.shields.io/badge/Language-English-blue?style=flat-square)](#-english)
[![KR](https://img.shields.io/badge/언어-한국어-red?style=flat-square)](#-한국어)

</div>

---

## 🇺🇸 English

A production backend for **WJMAX**, a fan-made rhythm game in the Woowakgood community. Joined the main developer under a short-term collaboration request to design and operate the server architecture, security layer, and database infrastructure needed to sustain high-traffic gameplay.

### 📋 Project Overview

Built and operated a scalable backend stack capable of absorbing real-time traffic spikes during service peaks. Responsibilities spanned infrastructure design, edge-level security hardening, and high-volume log collection to support data-driven service monitoring.

- **Role:** Backend server, security, and database engineering
- **Scale:** Sustained 3,000+ peak concurrent users
- **Key Outcome:** Scalable AWS-based infrastructure hardened with a Cloudflare edge layer

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
- **AWS RDS (MySQL)** — Separated the database layer onto managed RDS to secure data durability, availability, and independent scalability.

#### 2. Security & Network
- **Cloudflare Edge Layer** — Applied DNS management and Cloudflare's WAF/proxy in front of the origin, shielding the server from external attacks and absorbing traffic bursts before they reached the application.

#### 3. High-Volume Log Collection
- Operated an efficient collection pipeline for the large log volume produced during live service, laying the groundwork for data visualization and real-time service health monitoring.

### 🏗 System Architecture

> The repository contains the initial prototype code. The production deployment was structured as follows:
> **Client → Cloudflare (WAF + Proxy) → AWS EC2 (FastAPI on Docker) → AWS RDS (MySQL)**

1. **Traffic Entry** — Cloudflare (WAF & Proxy)
2. **Application Layer** — AWS EC2 running FastAPI inside Docker
3. **Data Layer** — AWS RDS (managed MySQL)

<div align="right"><a href="#-한국어">🇰🇷 한국어로 보기 ↓</a></div>

---

## 🇰🇷 한국어

우왁굳 팬게임 **'왁제이맥스(WJMAX)'**의 운영 백엔드입니다. 메인 개발자의 협업 요청으로 단기 투입되어, 대규모 트래픽을 견디기 위한 서버 아키텍처, 보안 계층, 데이터베이스 인프라 설계 및 운영을 담당했습니다.

### 📋 프로젝트 개요

서비스 피크 시간대의 실시간 트래픽을 흡수할 수 있는 확장 가능한 백엔드 스택을 구축하고 운영했습니다. 인프라 설계, 엣지 레벨 보안 강화, 대용량 로그 수집까지 서비스 모니터링 기반을 포괄적으로 담당했습니다.

- **역할:** 백엔드 서버, 보안, 데이터베이스 엔지니어링
- **규모:** 피크 동시 접속자 3,000명 이상 대응
- **핵심 성과:** AWS 기반 확장성 있는 인프라 구축 및 Cloudflare 엣지 계층을 통한 보안 강화

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
- **AWS RDS (MySQL)** — 데이터베이스 계층을 Managed RDS로 분리하여 데이터 내구성, 가용성, 독립적인 확장성을 확보했습니다.

#### 2. 보안 및 네트워크
- **Cloudflare 엣지 계층** — 오리진 앞단에 DNS 관리 및 Cloudflare의 WAF/Proxy를 적용하여 외부 공격으로부터 서버를 보호하고, 애플리케이션 레이어 도달 전 트래픽 버스트를 흡수했습니다.

#### 3. 대용량 로그 수집
- 라이브 서비스에서 발생하는 대규모 로그를 효율적으로 수집하는 파이프라인을 운영하여, 데이터 시각화 및 실시간 서비스 상태 모니터링 기반을 마련했습니다.

### 🏗 시스템 아키텍처

> 본 리포지토리에는 초기 프로토타입 코드가 포함되어 있으며, 실제 운영 환경은 아래와 같이 구성되었습니다.
> **Client → Cloudflare (WAF + Proxy) → AWS EC2 (FastAPI on Docker) → AWS RDS (MySQL)**

1. **트래픽 진입** — Cloudflare (WAF & Proxy)
2. **애플리케이션 계층** — AWS EC2에서 Docker 기반 FastAPI 구동
3. **데이터 계층** — AWS RDS (Managed MySQL)

<div align="right"><a href="#-english">🇺🇸 View in English ↑</a></div>
