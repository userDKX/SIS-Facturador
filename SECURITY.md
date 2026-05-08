# Seguridad

## Reportar una vulnerabilidad

Si encuentras una vulnerabilidad de seguridad en **SIS Facturador**, no abras
un issue público. En su lugar:

- Abre un [reporte privado de seguridad](https://github.com/userDKX/SIS-Facturador/security/advisories/new)
  en este repo, o
- Escríbele al mantenedor (contacto en el perfil de GitHub).

La meta es responder en 72 horas y publicar un fix o mitigación dentro de 14
días para issues críticos.

Cuando puedas, incluye en el reporte:

- Versión afectada (commit SHA o tag).
- Pasos para reproducir o PoC.
- Impacto: qué puede hacer un atacante.

## Versiones soportadas

Hasta que el proyecto llegue a `1.0.0`, solo se soporta el último minor.

| Versión | Soportada |
|---------|-----------|
| `0.1.x` | Sí        |

## Material sensible

Este proyecto firma y envía documentos tributarios reales a SUNAT. Lo que
sigue **nunca** debe terminar en un commit, en un log, ni compartirse:

| Qué                              | Dónde vive                            | Notas                                                  |
|----------------------------------|---------------------------------------|--------------------------------------------------------|
| Certificado digital `.pfx`       | env var `CERT_PFX_BASE64` (base64)    | No en disco. No en BD. No en logs.                     |
| Password del certificado         | env var `CERT_PASSWORD`               | Distinta de la clave SOL.                              |
| Clave del usuario secundario SOL | env var `SUNAT_PASSWORD`              | Si se filtra, rotar de inmediato.                      |
| Connection string de la BD       | env var `DATABASE_URL`                | El service key solo en el server, nunca en cliente.    |
| Service key de Supabase          | env var `SUPABASE_SERVICE_KEY`        | Bypassa RLS — nunca exponerlo al cliente.              |
| XMLs firmados y CDRs             | `storage/` (gitignored)               | Tienen RUCs, montos y datos del cliente reales.        |

El `.gitignore` del repo ya excluye `.env`, `*.pfx`, `*.p12`, `*.pem`,
`*.key`, `*.crt` y `storage/`. Igual revisa con `git status` antes de
commitear.

## Respuesta ante incidentes

### Si el certificado se compromete

1. Revoca el cert con la CA emisora (RENIEC para los certs ECEP-RENIEC),
   ahora mismo.
2. Genera uno nuevo y vuelve a registrarlo en SOL producción:
   *Empresas → Comprobantes de Pago → SEE-DSC → Servicio de Envío de
   Documentos Electrónicos → Registre aquí su certificado digital*.
3. Actualiza `CERT_PFX_BASE64` y `CERT_PASSWORD` en cada deploy.
4. Audita los últimos 30 días en *Consultar Envíos de CPE* por envíos que no
   reconozcas.

### Si la clave SOL se compromete

1. Entra al SOL con el usuario primario y resetea la clave del secundario.
2. Actualiza `SUNAT_PASSWORD` en cada deploy.
3. Espera la propagación estándar de SUNAT (hasta 24 horas calendario) antes
   de reanudar envíos por WS — antes de eso pueden venir `0102` o `0111`.

## Modelo de amenazas (deploy single-tenant en Vercel)

- **Superficie pública**: endpoints HTTPS expuestos por Vercel; en el modelo
  actual no hay auth en la API — asume que el deploy solo es alcanzable
  desde callers de confianza (el backend del SIS por firewall de salida, o
  una VPN).
- **Datos en reposo**: Supabase Postgres (managed, encriptado) + bucket de
  Supabase Storage con acceso solo por service key (bypass RLS).
- **Datos en tránsito**: TLS 1.2+ a Vercel; TLS 1.2+ a SUNAT.
- **Secretos**: env vars en Vercel (encriptados en reposo). El `.pfx` nunca
  toca disco.
- **Fuera de alcance** del release actual: auth por API key, isolation por
  tenant, audit logs, rate limiting. Todo eso es parte del modo provider
  multi-tenant (ver `docs/DEPLOY_PROVIDER.md`).
