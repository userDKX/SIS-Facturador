# Documentación

Documentación del **SIS Facturador**, una API en Python para emitir
comprobantes electrónicos a SUNAT (Perú). Está pensada para tres tipos de
lectores: el que necesita usarlo (operador), el que quiere evaluarlo
(reviewer / recruiter), y el que quiere extenderlo (contribuidor).

## Por dónde empezar

| Si quieres…                                                          | Léete                                       |
|----------------------------------------------------------------------|---------------------------------------------|
| Correr el API en local en 10 minutos                                 | [`INSTALL.md`](./INSTALL.md)                |
| Habilitar un RUC real en producción (crear secundario, permisos…)    | [`SUNAT_SETUP.md`](./SUNAT_SETUP.md)        |
| Entender la forma del código                                         | [`ARCHITECTURE.md`](./ARCHITECTURE.md)      |
| Diagnosticar un código de error de SUNAT (`0111`, `2800`, `3244`…)   | [`TROUBLESHOOTING.md`](./TROUBLESHOOTING.md)|

## Lado técnico

| Tema                                                                 | Doc                                         |
|----------------------------------------------------------------------|---------------------------------------------|
| Por qué SUNAT usa XMLDSig y no XAdES, y cómo lo firmamos             | [`SIGNING.md`](./SIGNING.md)                |
| Detalles de UBL 2.1 que SUNAT valida                                 | [`UBL.md`](./UBL.md)                        |
| El protocolo SOAP, los códigos de error, marco normativo 2024-2026   | [`SUNAT.md`](./SUNAT.md)                    |
| Referencia HTTP de la API                                            | [`API.md`](./API.md)                        |

## Despliegue

| Modo                                                                 | Doc                                         |
|----------------------------------------------------------------------|---------------------------------------------|
| Single-tenant en Vercel (lo implementado)                            | [`DEPLOY_VERCEL.md`](./DEPLOY_VERCEL.md)    |
| Multi-tenant provider en Kubernetes (conceptual, sin código aún)     | [`DEPLOY_PROVIDER.md`](./DEPLOY_PROVIDER.md)|

## Sobre estos docs

Markdown plano, GitHub-flavored. Los diagramas Mermaid renderizan directo en
GitHub.

Los snippets son código real del repo. Si en algún punto la doc dice algo
distinto al código, gana el código — la doc se mantiene sincronizada pero la
fuente de verdad vive en `app/`.

Todo está en español porque la audiencia natural es el dev peruano que está
empezando con SUNAT. Si te resulta útil traducir alguno al inglés para
alcance internacional, los PRs son bienvenidos.
