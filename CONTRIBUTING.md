# Contribuir al SIS Facturador

Gracias por considerar contribuir. Este doc explica cómo trabajar con el
repo: cómo armar el entorno, qué convenciones seguimos, cómo abrir un PR.

## Empezar

Antes de tocar código, tener listo el entorno:

```bash
git clone https://github.com/userDKX/SIS-Facturador.git
cd SIS-Facturador
python -m venv .venv
source .venv/bin/activate    # o .\.venv\Scripts\Activate.ps1 en Windows
pip install -e ".[dev]"
```

Si tienes pre-commit instalado y quieres activarlo en este repo:

```bash
pre-commit install
```

(Opcional, pero recomendado — corre ruff + mypy automáticamente antes de
cada commit.)

## Cómo trabajar

1. **Abre o reclama una issue** antes de meter horas. Si es algo chico
   (typo, fix de un párrafo en docs), salta este paso y manda PR directo.
2. **Crea un branch** desde `main`:
   ```bash
   git checkout -b feat/notas-credito
   # o:  git checkout -b fix/cdr-encoding
   ```
3. **Hacer cambios pequeños y enfocados.** Mejor 3 PRs chicos que uno
   gigante.
4. **Antes de pushear**: corre `make lint` y `make test`. Ambos deben pasar.
5. **Push y abre PR** contra `main`. La plantilla del PR te indica qué
   incluir.

## Convenciones de código

- **Lint y format**: `ruff` (config en `pyproject.toml`). Antes de
  commitear: `make fmt`.
- **Tipos**: `mypy` strict en `app/` (lenient en `tests/` y `scripts/`).
  Si agregas dependencias sin stubs (zeep, signxml), el `ignore_missing_imports`
  global te cubre.
- **Tests**: `pytest`. Tests de SUNAT real con marker `@pytest.mark.beta`
  para que CI los skipee (necesitan envs y cert real). Unit tests del builder
  y signer pueden correr sin red.
- **Comentarios y docstrings en español** cuando aporten contexto. Las
  identificadoras en código siguen lo que ya está (mezcla de español e
  inglés según el módulo).

## Convenciones de commits (Conventional Commits)

```
feat: nueva funcionalidad
fix: bug fix
chore: tarea sin impacto en código (deps, config)
docs: solo documentación
style: formato sin cambio funcional
refactor: cambio de código sin cambiar comportamiento
test: solo tests
ci: cambios en pipeline / workflows
perf: mejora de performance
```

El primer renglón en imperativo, < 72 chars. Cuerpo opcional, en español
o inglés según prefieras (preferencia: español para que combine con la
doc).

Ejemplo:

```
feat(api): soporte de notas de crédito tipo 07

Agrega POST /v1/credit-notes que arma UBL CreditNote, firma y envía
sendBill. Tabla credit_notes con FK a invoices.

closes #42
```

## Tests

```bash
# unit + integration sin tocar SUNAT (lo que corre CI)
make test

# coverage HTML
make cov

# tests contra SUNAT beta (requiere MODDATOS configurado en .env)
make test-beta
```

Si tu cambio agrega lógica al builder, signer o sunat client, agrega
tests. Si toca un endpoint, agrega tests e2e en `tests/e2e/`.

## Cuando tu PR toca documentación

- Texto en **español natural**, no traducciones literales del inglés.
- Sin emojis decorativos en headers ni listas. Sin frases tipo "Welcome
  to…", "This guide will walk you through…". Tono dev-a-dev directo.
- Si introduces concepto nuevo, agrégalo al lugar correcto:
  - Cómo instalar/usar → `docs/INSTALL.md`
  - Onboarding SUNAT del titular → `docs/SUNAT_SETUP.md`
  - Detalle del flujo SOAP → `docs/SUNAT.md`
  - Cualquier error nuevo → `docs/TROUBLESHOOTING.md`

## Cuando agregas un nuevo tipo de comprobante

(Roadmap incluye NC `07`, ND `08`, comunicación de baja, resumen diario.)

Cosas a tocar como mínimo. Importante: separar lo que es lógica del estándar
SUNAT (va al SDK `sunat_py`) de lo que es del servicio HTTP (va a
`sis_facturador`).

En el **SDK** (`packages/core/src/sunat_py/`):

- `ubl/templates/` — plantilla nueva (si la estructura difiere de Invoice
  2.1, ej. CreditNote 2.1)
- `ubl/builder.py` — función `build_*_xml` nueva
- `ubl/models.py` — dataclass nuevo
- `__init__.py` — re-export del nuevo símbolo

En el **microservicio** (`packages/api/src/sis_facturador/`):

- `schemas/` — Pydantic schemas del request/response
- `services/` — orquestador (si difiere de `create_and_send`)
- `routers/` — endpoint nuevo
- `models/` — tabla nueva (con migration en `migrations/`)

Y además:

- `packages/core/tests/unit/test_*_builder.py` — tests unit del builder
- `packages/api/tests/e2e/` — tests e2e del endpoint
- `examples/` — payload de ejemplo
- `docs/UBL.md` — sección sobre el nuevo comprobante
- `docs/API.md` — endpoint documentado
- `CHANGELOG.md` — entrada bajo `[Sin publicar]`

## Cuando algo te frustra

Las cosas raras de SUNAT son normales — la doc oficial es ambigua, el
portal SOL es lento, los mensajes de error son crípticos. Si encuentras
algo que te tomó horas resolver, **documéntalo** en
`docs/TROUBLESHOOTING.md` o `docs/SUNAT.md`. La próxima persona te lo va
a agradecer.

## Reportar problemas de seguridad

No abras issue público. Sigue lo descrito en [`SECURITY.md`](./SECURITY.md).

## Licencia

Al contribuir aceptas que tu código se distribuya bajo la
[licencia MIT](./LICENSE) del proyecto.
