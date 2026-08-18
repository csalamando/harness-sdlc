# Requisitos de Seguridad

| ID | Requisito | Verificación |
|---|---|---|
| SEC-001 | Autenticación: <método>, tokens con expiración <n> | Test E2E + revisión |
| SEC-002 | Autorización: control de acceso por <modelo> en cada endpoint | Contract tests |
| SEC-003 | Cifrado TLS 1.2+ en tránsito; AES-256 en reposo | Config + ZAP |
| SEC-004 | Secretos solo en gestor de secretos; prohibidos en repo/logs | gitleaks + revisión |
| SEC-005 | Logs sin PII ni credenciales | SAST + revisión |
