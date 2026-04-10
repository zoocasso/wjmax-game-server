# 🎹 WJMAX Backend & Database Engineering
> **우왁굳 팬게임 '왁제이맥스(WJMAX)' 서버 구축 및 최적화**
> 
> 메인 개발자의 협업 요청으로 단기 투입되어, 대용량 트래픽 대응을 위한 서버 아키텍처 구축 및 보안 솔루션을 담당했습니다.

---

## 📋 프로젝트 개요 (Project Overview)
'왁제이맥스' 서비스의 안정적인 운영을 위해 백엔드 API 서버를 구축하고, 발생하는 대규모 트래픽 로그를 수집하여 데이터 시각화를 처리하는 인프라 최적화 작업을 수행했습니다.

* **역할:** 서버 구축, 보안 설정, 데이터베이스 관리 (Server, Security, DB Management)
* **핵심 성과:** AWS 기반의 확장성 있는 인프라 구축 및 Cloudflare를 통한 보안 강화

## 🛠 기술 스택 (Tech Stack)
* **Framework:** FastAPI
* **Container:** Docker
* **Cloud & Infra:** AWS (EC2, RDS), Cloudflare
* **Database:** MySQL (AWS RDS)

## ✨ 주요 수행 업무 (Key Responsibilities)

### 1. 인프라 설계 및 배포 (Infra & Deployment)
* **AWS EC2 & Docker:** FastAPI 서버를 컨테이너화하여 일관된 실행 환경을 보장하고 배포 효율성을 높였습니다.
* **AWS RDS (MySQL):** 데이터베이스를 분리 구축하여 데이터의 안정성과 확장성을 확보했습니다.

### 2. 보안 및 네트워크 (Security & Network)
* **Cloudflare 적용:** DNS 관리 및 Cloudflare 보안 계층을 적용하여 외부 공격으로부터 서버를 보호하고 트래픽을 효율적으로 관리했습니다.

### 3. 대용량 트래픽 로그 수집 (Log Analysis)
* 서비스 운영 중 발생하는 대용량 로그를 효율적으로 수집하고, 이를 기반으로 서비스 상태를 파악할 수 있는 데이터 시각화 기반을 마련했습니다.

---

## 🏗 시스템 아키텍처 (Architecture)
> 현재 리포지토리에는 초기 프로토타입 코드가 업로드되어 있으며, 실제 운영 환경은 아래와 같이 구성되었습니다.

1.  **Traffic Entry:** Cloudflare (WAF & Proxy)
2.  **Web Server:** AWS EC2 (FastAPI running on Docker)
3.  **Database:** AWS RDS (MySQL Managed Service)

---
