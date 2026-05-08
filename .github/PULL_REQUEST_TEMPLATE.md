<!--
Gracias por contribuir. Llena lo que aplique. Si es un fix puntual,
basta con la sección "Qué cambia" y "Cómo probarlo".
-->

## Qué cambia

<!-- 1-3 líneas. Sin marketing. -->

## Por qué

<!-- El motivo. Si hay issue relacionada, ponla acá: closes #123 -->

## Cómo probarlo

<!--
Pasos concretos para que el reviewer reproduzca:
- Comandos exactos
- Endpoints y payloads si aplica
- Resultados esperados
-->

## Checklist

- [ ] `make lint` y `make test` pasan en local
- [ ] Si toqué `app/`, agregué/actualicé tests cuando aplica
- [ ] Si toqué la API HTTP, actualicé `docs/API.md` y/o `examples/`
- [ ] Si introduce config nueva, está en `.env.example` y documentada en `docs/INSTALL.md` o `docs/DEPLOY_VERCEL.md`
- [ ] Si afecta el flujo de SUNAT, agregué nota en `docs/SUNAT.md` o `docs/TROUBLESHOOTING.md`
- [ ] El commit message sigue Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, etc.)

## Notas para el reviewer

<!-- Cosas que conviene saber al revisar: decisiones de diseño, alternativas que descartaste, gotchas. -->
