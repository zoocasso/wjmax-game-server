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
