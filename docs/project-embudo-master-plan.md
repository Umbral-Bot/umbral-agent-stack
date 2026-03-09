# Master Plan: Proyecto Embudo (V2) - Rick AI Stack

## 1. Objetivo
Desarrollar un sistema autónomo de captación, marketing y ventas basado en IA para los servicios de David Moreira, fundamentado en datos reales del mercado y una identidad de marca coherente extraída del perfil de David.

## 2. Fase 1: Extracción de Identidad y Análisis de Perfil (Prioridad Máxima)
- **Agente Responsable:** Rick-Tracker / Rick-Ops
- **Acción:** Analizar la carpeta `G:\Mi unidad\Rick-David\Perfil de David Moreira` en la VM Windows.
- **Resultado esperado:** Documento maestro de Identidad, Servicios, Experiencia y Vibe de David.

## 3. Fase 2: Investigación de Mercado e Inteligencia de Oportunidades
- **Agente Responsable:** Rick-QA
- **Herramientas:** Google Search API, Tavily, n8n Scraping, Vertex AI.
- **Acción:** Investigar tendencias en AEC y Automatización IA en España/LATAM. Identificar "gaps" de mercado.
- **Resultado esperado:** Informe de Oportunidades Comerciales Reales.

## 4. Fase 3: Estrategia de Marketing y Embudo de Ventas
- **Agente Responsable:** Rick-Delivery / Marketing Agent
- **Acción:** Diseñar el flujo desde el Portal AEC News (Ghost) hacia la conversión. Definir canales, separar fuentes de autoridad vs referentes de divulgación y operar primero una fase editorial manual antes de automatizar.
- **Resultado esperado:** Roadmap de contenidos, shortlist editorial alineada con la narrativa, propuesta y audiencia de David, y una fase 1 manual validada para blog, newsletter y LinkedIn.
- **Referencia:** Ver [docs/67-editorial-source-curation.md](67-editorial-source-curation.md).

## 5. Fase 4: Implementación AEC Tech Portal (UMB-19)
- **Agente Responsable:** Rick-Ops
- **Acción:** Puesta en marcha de Ghost CMS y, solo cuando la fase manual sea estable, configuración de flujos n8n para curación asistida. La automatización queda subordinada a shortlist humana, gating editorial y validación previa del valor real del flujo.

## 6. Estado de Tareas (Linear)
- [ ] UMB-19: Arquitectura Ghost + Newsletter
- [ ] (Pendiente) UMB-20: Extracción de Perfil de Identidad (David Moreira)
- [ ] (Pendiente) UMB-21: Investigación de Mercado AEC/IA 2026
