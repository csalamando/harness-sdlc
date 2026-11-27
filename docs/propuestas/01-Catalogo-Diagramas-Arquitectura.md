# Catálogo de diagramas de arquitectura

> Plantilla guía PLT-01 · Versión 2.7 · Dueño: Jefatura de Arquitectura e Interoperabilidad
> v1.2: ejemplos Mermaid embebidos y renderizables en la wiki (D1, D4, D6, D7), enlazados a sus fuentes parametrizadas.
> v1.3: ejemplos renderizados de D2, D3, D5, D8 y mapa de dependencias (Python diagrams) embebidos como imagen; icono APISIX reemplazado por Kong (removido en diagrams ≥ 0.25).
> v2.0: **D6 pasa de modelo entidad-relación a Diagrama de Flujo de Datos (DFD)** con clasificación según Ley 1581-2012 y protección por tramo; tabla de **atributos exigibles en todos los diagramas** (no solo D3); los scripts parametrizados incorporan un **validador automático** (`_exigibles.py`) que verifica el contenido exigible antes de generar la imagen.
> v2.1: **tablas complementarias** para no saturar las cajas: el D6 lleva tabla de sistemas y almacenes (clasificación, motor/tipo de BD, cifrado en reposo) y el mapa de dependencias genera tabla aplicación ↔ servicio con totales.
> v2.2: **sistema de diseño visual** (§7): paleta institucional, fuente y estilos por rol semántico, centralizados en `_estilos.py` (Python) y `_estilos.mmd` (Mermaid) — los diagramas dejan de definir colores propios.
> v2.3: **reglas de legibilidad** (§7) tras revisar los diagramas renderizados en la wiki: tipografías grandes (título 26pt Semibold, nodo 14pt, arista 12pt, 150 dpi), classDef obligatorio en todo nodo Mermaid (adiós lavanda por defecto), etiquetas largas en dos líneas, rojo reservado a riesgo.
> v2.4: **convención de bordes y ubicación** (§7): todo recuadro redondeado; continua = gobierno del banco, punteada = fuera de control; color por nube (AWS/Azure) y on-premise; usuarios internos/externos diferenciados.
> v2.5: se **retira la leyenda embebida** (rompía layout y estética); la convención de colores vive en §7 y las páginas de la wiki la enlazan.
> v2.6: D8 gana **tabla complementaria de certificados y secretos** (ubicación en vault, responsable, vigencia y rotación — generada por el script y validada como exigible).
> v2.7: **D2 y D3 también generan su tabla complementaria** (componentes con rol y stack en D2; componentes por zona/plataforma con detalle de seguridad en D3) — los cinco scripts Python producen imagen + tabla Markdown.
> Propósito: definir qué diagramas se crean y mantienen por iniciativa, cuáles son obligatorios, qué debe contener cada uno y cuándo se actualizan.
> Regla de oro: **cada diagrama responde una pregunta concreta**. Si un diagrama no responde ninguna pregunta, no se hace; si la pregunta existe, el diagrama no es opcional.

---

## 1. Problema que resuelve este catálogo

Hoy conviven diagramas C4 niveles 1 y 2 con diagramas funcionales en mermaid, pero con vacíos recurrentes: no se ve **dónde está desplegado** cada elemento, **en qué nube y en qué cuenta**, **a cargo de quién**, los **nombres reales** de servicios y componentes, los **protocolos de seguridad** y **certificados**, ni el **stack tecnológico**. Este catálogo convierte esos vacíos en contenido mínimo exigible, sin pedir diagramas de más.

## 2. Convenciones comunes (aplican a todo diagrama)

1. **Ficha del diagrama**: todo diagrama lleva un bloque visible con: iniciativa (INI-####), ambiente que representa, fecha de actualización y responsable (persona).
2. **Nombres reales**: los nodos se llaman como se llaman en la realidad (nombre del servicio en el clúster, del API en el gateway, de la base de datos). Nada de cajas genéricas tipo "Backend" o "Servicio 1".
3. **Herramienta y fuente**: topología, infraestructura, despliegue y mapas de nodos/servicios en **Python diagrams** (D2, D3, D5, D8 y dependencias de APIs) — el fuente Python se versiona en el repo y la imagen se exporta a la wiki; todo lo demás en **mermaid** (D1, D4, D6, D7) embebido en la wiki. Ambas rutas tienen **plantillas parametrizadas** en `skills/diagramas-arquitectura/scripts/`: se edita un bloque de configuración, no se escribe código desde cero.
   > **Sintaxis mermaid en la wiki de Azure DevOps** (corre Mermaid 8.13.9): se embebe con `::: mermaid` … `:::` (NO con la valla ` ```mermaid ` de GitHub); se usa `graph` (NO `flowchart`); la primera línea del bloque debe ser el tipo de diagrama (un comentario `%%` inicial rompe el render con "Unsupported diagram type" — la ficha va como texto visible encima del bloque).
4. **Leyenda mínima**: si el diagrama usa colores o formas con significado, la leyenda va en la misma imagen.
5. **Un diagrama, una página dueña**: el diagrama vive en el DAS o en su página de anexo; las demás páginas lo enlazan, no lo copian.

## 3. Tabla resumen: obligatoriedad por tipo de iniciativa

| # | Diagrama | Pregunta que responde | Tipo A (estratégica) | Tipo B (evolutiva) | Tipo C (menor) |
|---|---|---|---|---|---|
| D1 | Contexto de negocio y usuarios | ¿Quién usa esto y para qué existe? | **Obligatorio** | **Obligatorio** | **Obligatorio** (simple) |
| D2 | Contenedores y servicios (C4 N2) | ¿De qué piezas se compone y con qué stack? | **Obligatorio** | **Obligatorio** | Solo si cambia la estructura |
| D3 | Despliegue e infraestructura | ¿Dónde corre, en qué cuenta, a cargo de quién? | **Obligatorio** | **Obligatorio** | Solo si cambia el despliegue |
| D4 | Flujos funcionales principales | ¿Cómo viaja la operación del usuario? | **Obligatorio** | **Obligatorio** | Opcional |
| D5 | Integración y mensajería | ¿Con qué sistemas habla, por qué protocolo? | **Obligatorio** | **Obligatorio** si hay integraciones | Opcional |
| D6 | Flujo de datos (DFD) | ¿De dónde vienen los datos, a dónde van, qué tan sensibles son y cómo viajan protegidos? | **Obligatorio** si maneja datos sensibles | Opcional | Opcional |
| D7 | Componentes internos (C4 N3) | ¿Cómo está armado por dentro el componente crítico? | Solo componentes críticos | Opcional | No |
| D8 | Seguridad y fronteras de confianza | ¿Dónde cruzan los datos zonas de distinta confianza? | **Obligatorio** | Opcional | No |

## 4. Contenido mínimo de cada diagrama

### D1 · Contexto de negocio y usuarios (C4 N1 adaptado)

- Usuarios con nombre de rol real (no "usuario genérico"): cliente persona natural, asesor comercial, funcionario backoffice…
- La necesidad de negocio que se atiende, en una frase dentro del diagrama o su pie.
- Sistemas externos y del banco con los que interactúa la solución.
- **No técnico por diseño**: este es el diagrama que negocio, Director y VP deben entender sin ayuda.

| Atributo exigible | Ejemplo |
|---|---|
| Roles de usuario reales (no "usuario") | `Cliente persona natural`, `Asesor comercial` |
| Necesidad de negocio en una frase | *"Permite al cliente autogestionar sus productos sin ir a la oficina"* |
| Sistemas del banco y terceros con nombre real | `Core bancario`, `CRM comercial`, `Proveedor OTP` |
| Cero jerga técnica (legible por negocio) | Sin nombres de clúster, pods ni protocolos |
| Ficha del diagrama | `INI-0000 · 2026-01-01 · Responsable` |

**Ejemplo** (fuente parametrizada: `skills/diagramas-arquitectura/scripts/mermaid/d1_contexto.mmd` — se edita el bloque de actores y sistemas, no se dibuja desde cero):

**Ficha: INI-0000 · 2026-01-01 · Responsable**

::: mermaid
graph LR
    subgraph usuarios["Usuarios"]
        cliente["Cliente persona natural"]
        asesor["Asesor comercial"]
    end

    subgraph solucion["La solución"]
        app["App Banca Móvil<br/><i>Permite al cliente autogestionar sus productos sin ir a la oficina</i>"]
    end

    subgraph banco["Sistemas del banco"]
        core["Core bancario"]
        crm["CRM comercial"]
    end

    subgraph externos["Terceros"]
        otp["Proveedor OTP"]
    end

    cliente -->|consulta y opera| app
    asesor -->|acompaña| app
    app --> core
    app --> crm
    app --> otp

    style solucion fill:#E4F2EA,stroke:#008643,stroke-width:2px
    style banco fill:#F2F8F4,stroke:#006332,stroke-width:1.5px
    style externos fill:#F5F6F5,stroke:#5F6E65,stroke-dasharray:5 5
    style usuarios fill:#FFFFFF,stroke:#C4D8CE
    classDef nodo fill:#FFFFFF,stroke:#C4D8CE,color:#1E2A24;
    classDef nodoSolucion fill:#E4F2EA,stroke:#008643,stroke-width:2px,color:#1E2A24;
    classDef banco fill:#F2F8F4,stroke:#006332,color:#1E2A24;
    classDef externo fill:#F5F6F5,stroke:#5F6E65,stroke-dasharray:5 5,color:#1E2A24;
    class cliente,asesor nodo
    class app nodoSolucion
    class core,crm banco
    class otp externo
:::

### D2 · Contenedores y servicios (C4 N2)

- Cada contenedor/servicio con **nombre real** y **stack tecnológico** (ej.: `api-tarjetas · Node 20 · EKS`, `spa-canales · Angular 17`).
- Comunicaciones con **protocolo** explícito (HTTPS/REST, AMQP, gRPC, JDBC…).
- Bases de datos y almacenes con motor y versión.
- Referencia al catálogo de tecnología (C3) para versiones y fin de soporte.

| Atributo exigible | Ejemplo |
|---|---|
| Nombre real por contenedor (como está desplegado) | `api-tarjetas`, `spa-canales` |
| Stack tecnológico en cada nodo | `Node 20 · EKS`, `Angular 17` |
| Protocolo en cada conexión | `HTTPS/REST`, `AMQP`, `JDBC` |
| Motor y versión en almacenes de datos | `PostgreSQL 15`, `Redis 7` |
| Referencia al catálogo C3 (versión y fin de soporte) | `C3 · Node 20 · soporte hasta 2026-04` |
| Ficha del diagrama | `INI-0000 · PRD · 2026-01-01 · Responsable` |

El script `d2_contenedores.py` verifica estos atributos automáticamente antes de generar la imagen (ver §6).

**Ejemplo** (fuente parametrizada: `skills/diagramas-arquitectura/scripts/d2_contenedores.py` — se edita el bloque CONFIG y las listas, se regenera con `python d2_contenedores.py`; genera la imagen y la tabla complementaria `D2_contenedores_tabla.md`):

![D2 · Contenedores y servicios](img/D2_contenedores.png)

**Tabla complementaria · componentes**

| Componente | Rol | Stack / detalle |
|---|---|---|
| Cliente persona natural | Actor | — |
| spa-canales | Servicio | Angular 17 |
| canales-api-bff | Servicio | Node 20 |
| motor-tarjetas | Servicio | Java 21 · Spring Boot 3 |
| canales-db | Almacén de datos | PostgreSQL 15.4 |
| Core bancario (on-premise) | Sistema del banco / externo | — |

### D3 · Despliegue e infraestructura

El diagrama que hoy falta. Debe mostrar, como mínimo:

| Elemento exigible | Ejemplo |
|---|---|
| Nube o on-premise, con **cuenta/suscripción** | `AWS · cuenta banco-prod-canales (123456)` |
| Región / zona | `us-east-1` |
| Plataforma de ejecución y namespace/clúster | `EKS · cluster prod-01 · ns-tarjetas` |
| Componentes de red y exposición | API Gateway, WAF, balanceadores, VPC/subredes |
| **Responsable operativo** de cada zona | `Operaciones TI · guardia canales` |
| Protocolos de seguridad por salto | `TLS 1.3`, `mTLS`, `JWT (Entra ID)` |
| **Certificados**: cuáles, emisor y dónde se guardan (ruta del vault, nunca el valor) | `cert api.banco.com · ACM · vault:/prod/tls` |
| Ambientes cubiertos | Indicar si aplica a QA/prod o hacer uno por ambiente crítico |

**Ejemplo** (fuente: `skills/diagramas-arquitectura/scripts/d3_despliegue.py` — genera la imagen y la tabla complementaria `D3_despliegue_prd_tabla.md`):

![D3 · Despliegue e infraestructura](img/D3_despliegue_prd.png)

**Tabla complementaria · componentes por zona**

| Componente | Zona / plataforma | Detalle |
|---|---|---|
| WAF | Internet / canales | WAF · reglas OWASP |
| API Gateway | AWS · cuenta banco-canales-prod (123456789) · us-east-1 | API Gateway · TLS 1.3 · JWT (Entra ID) · cert api.banco.com · ACM · vault:/prod/tls |
| canales-api-bff | EKS · cluster prod-01 · ns-canales | Servicio desplegado |
| spa-canales | EKS · cluster prod-01 · ns-canales | Servicio desplegado |
| canales-db | AWS · cuenta banco-canales-prod (123456789) · us-east-1 | canales-db · PostgreSQL 15.4 · Multi-AZ |
| Core bancario | On-premise | Core bancario · DC principal · Responsable: Operaciones TI · guardia core |

**Responsable operativo:** Operaciones TI · guardia canales

### D4 · Flujos funcionales principales (mermaid)

- El **flujo feliz** de la operación principal y al menos **un flujo de error o compensación** relevante.
- Actores y sistemas con los mismos nombres reales de D2/D3.
- Regla práctica: máximo 2–3 flujos por DAS; el resto va en anexos.

| Atributo exigible | Ejemplo |
|---|---|
| Flujo feliz de la operación principal | Transferencia exitosa de principio a fin |
| Al menos un flujo de error o compensación | `CORE--xINT: Fondos insuficientes` |
| Nombres idénticos a D2/D3 (misma solución, mismos nombres) | `canales-api-bff` en D2, D3 y D4 |
| Máximo 2–3 flujos por DAS | El resto en anexos |
| Ficha del diagrama | `INI-0000 · 2026-01-01 · Responsable` |

**Ejemplo** (fuente: `skills/diagramas-arquitectura/scripts/mermaid/d4_flujo.mmd`):

**Ficha: INI-0000 · 2026-01-01 · Responsable**

::: mermaid
sequenceDiagram
    autonumber
    actor C as Cliente persona natural
    participant SPA as spa-canales
    participant BFF as canales-api-bff
    participant INT as Framework de interoperabilidad
    participant CORE as Core bancario

    C->>SPA: Solicita transferencia
    SPA->>BFF: POST /Transfer/Initiate (JWT)
    BFF->>INT: /PaymentOrder/api/v4/Transfer/Initiate
    INT->>CORE: Débito y crédito
    CORE-->>INT: Confirmación
    INT-->>BFF: 200 OK
    BFF-->>SPA: Comprobante
    SPA-->>C: Transferencia exitosa

    rect rgb(253, 237, 236)
        note over BFF,CORE: Flujo de error / compensación
        CORE--xINT: Fondos insuficientes
        INT-->>BFF: 422 · código INSUF
        BFF-->>SPA: Error de negocio (sin datos técnicos)
        SPA-->>C: "No fue posible: saldo insuficiente"
    end
:::

### D5 · Integración y mensajería

- Cada integración con: sistema origen y destino, **servicio BIAN** que la expone (path), protocolo, patrón (sincrónico/evento/batch), y referencia a la ficha del catálogo de APIs (C2).
- Puede ser tabla + diagrama; para integraciones simples, la matriz de integración del DAS puede bastar sin diagrama.

| Atributo exigible | Ejemplo |
|---|---|
| Origen y destino reales por integración | `canales-api-bff → Framework de interoperabilidad` |
| Path BIAN del servicio | `/PaymentOrder/api/v4/Transfer/Initiate` |
| Referencia al catálogo C2 (o excepción EXC-####) | `SVC-0001` |
| Protocolo y patrón por integración | `HTTPS/REST · síncrono`, `Kafka · evento` |
| Ficha del diagrama | `INI-0000 · PRD · 2026-01-01 · Responsable` |

**Ejemplo** (fuente: `skills/diagramas-arquitectura/scripts/d5_integracion.py`). Existe además una variante de **mapa de dependencias entre APIs** (`dependencias_apis.py`), que se alimenta del catálogo C2 y genera **la imagen y una tabla resumen** (`dependencias_apis_tabla.md`) con el detalle aplicación ↔ servicio y los totales — la tabla evita llenar las cajas de texto:

![D5 · Integración y mensajería](img/D5_integracion.png)

![Mapa de dependencias de APIs](img/dependencias_apis.png)

| Aplicación consumidora | Servicio / API |
|---|---|
| APP-0002 · Canales Digitales | SVC-0001 · /CustomerContact/api/v4/Sms/Send |
| APP-0002 · Canales Digitales | SVC-0003 · /BranchLocationMgmt/api/v3/BranchLocation/Retrieve |
| APP-0005 · Banca Comercial | SVC-0003 · /BranchLocationMgmt/api/v3/BranchLocation/Retrieve |

**Total: 2 servicios · 2 aplicaciones consumidoras**

### D6 · Diagrama de Flujo de Datos (DFD)

El DFD es la vista de solución sobre los datos: de dónde vienen, a dónde van, qué tan sensibles son y cómo viajan protegidos. El modelo entidad-relación sigue existiendo, pero como **diseño detallado** (anexo del equipo de desarrollo); a nivel de solución lo que aporta valor a Arquitectura, Seguridad y Datos es el flujo.

- **Fuentes y destinos reales** de información; el detalle de cada uno (dato, clasificación, motor/tipo de base de datos, cifrado en reposo) va en la **tabla complementaria**, no en las cajas del diagrama.
- Cada flujo con **modo** (en línea / cercano a tiempo real / batch), **protocolo** y **cifrado en tránsito**.
- La solución declara qué datos sensibles **no persiste** (minimización).
- Enlazado al catálogo de dominios de datos (C4) que gobierna la Dirección de Datos.

| Atributo exigible | Ejemplo |
|---|---|
| Fuentes reales con el dato que aportan | `Core bancario · saldo, movimientos` |
| Destinos reales | `App Banca Móvil`, `Data lake analítico` |
| Clasificación Ley 1581-2012 por dato | `semiprivado`, `privado`, `sensible` |
| Motor y tipo de cada base de datos / almacén | `Oracle 19c · relacional`, `ADLS Gen2 · parquet` |
| Cifrado en reposo por fuente/destino que persiste | `AES-256 TDE`, `tokenización PCI` |
| Modo de transferencia por flujo | `en línea`, `cercano a tiempo real`, `batch` |
| Protocolo por flujo | `JDBC`, `HTTPS/REST`, `Kafka` |
| Cifrado en tránsito por flujo | `TLS 1.3`, `mTLS`, `TLS + SASL` |
| Minimización de datos sensibles | `BFF · no persiste datos sensibles` |
| Ficha del diagrama | `INI-0000 · PRD · 2026-01-01 · Responsable` |

**Ejemplo** (fuente parametrizada: `skills/diagramas-arquitectura/scripts/mermaid/d6_flujo_datos.mmd` — renderiza directamente en la wiki; la tabla complementaria va al final del fuente para copiarla en la página):

**Ficha: INI-0000 · PRD · 2026-01-01 · Responsable**

::: mermaid
graph LR
    subgraph fuentes["Fuentes de información"]
        core["Core bancario"]
        crm["CRM comercial"]
        tarjetas["Motor de tarjetas"]
    end

    subgraph solucion["La solución · canales-api-bff"]
        bff["BFF canales<br/><i>no persiste datos sensibles</i>"]
    end

    subgraph destinos["Destinos"]
        app["App Banca Móvil"]
        datalake["Data lake analítico"]
        otp["Proveedor OTP"]
    end

    core -->|"en línea · JDBC · TLS 1.3"| bff
    crm -->|"en línea · HTTPS/REST · mTLS"| bff
    tarjetas -->|"en línea · HTTPS · TLS 1.3"| bff
    bff -->|"en línea · HTTPS · TLS 1.3"| app
    bff -->|"cercano a tiempo real · Kafka · TLS + SASL"| datalake
    bff -->|"en línea · HTTPS · TLS 1.3"| otp

    style fuentes fill:#F2F8F4,stroke:#006332,stroke-width:1.5px
    style solucion fill:#E4F2EA,stroke:#008643,stroke-width:2px
    style destinos fill:#F5F6F5,stroke:#5F6E65,stroke-dasharray:5 5
    classDef nodo fill:#FFFFFF,stroke:#C4D8CE,color:#1E2A24;
    classDef nodoSolucion fill:#E4F2EA,stroke:#008643,stroke-width:2px,color:#1E2A24;
    classDef riesgo fill:#FDECEA,stroke:#BD1027,stroke-width:2px,color:#1E2A24;
    class core,crm,app,datalake,otp nodo
    class bff nodoSolucion
    class tarjetas riesgo
:::

**Tabla complementaria · sistemas y almacenes**

| Sistema | Rol | Datos | Clasificación (Ley 1581-2012) | Motor / tipo de BD | Cifrado en reposo |
|---|---|---|---|---|---|
| Core bancario | Fuente | saldo, movimientos | Semiprivado | Oracle 19c · relacional | AES-256 TDE |
| CRM comercial | Fuente | identificación, contacto | Privado | SQL Server 2019 · relacional | AES-256 |
| Motor de tarjetas | Fuente | PAN tokenizado | Sensible | Tokenización PCI | Vault PCI |
| App Banca Móvil | Destino | sesión efímera | Privado | Sin persistencia | — |
| Data lake analítico | Destino | movimientos anonimizados | Público | ADLS Gen2 · archivos parquet | AES-256 |
| Proveedor OTP | Destino | celular | Privado | N/A (tercero) | Responsabilidad del tercero |

### D7 · Componentes internos (C4 N3)

- Solo para el componente cuya lógica interna sea riesgosa, novedosa o costosa de entender leyendo código. No se documenta todo el sistema a este nivel.

| Atributo exigible | Ejemplo |
|---|---|
| Solo el componente crítico (justificado) | `canales-api-bff` — orquesta 6 servicios BIAN |
| Responsabilidad en una línea por componente interno | `Orquestador · compone llamadas a servicios BIAN` |
| Interacciones internas visibles | `router → validador → orquestador` |
| Justificación de por qué se documenta a este nivel | En el texto del DAS, junto al diagrama |
| Ficha del diagrama | `INI-0000 · 2026-01-01 · Responsable · Componente` |

**Ejemplo** (fuente: `skills/diagramas-arquitectura/scripts/mermaid/d7_componentes.mmd`):

**Ficha: INI-0000 · 2026-01-01 · Responsable · Componente: canales-api-bff**

::: mermaid
graph TB
    subgraph bff["canales-api-bff · Node 20"]
        router["Router de endpoints<br/><i>valida JWT y scopes</i>"]
        validador["Validador de negocio<br/><i>reglas de campos y límites</i>"]
        orquestador["Orquestador<br/><i>compone llamadas a servicios BIAN</i>"]
        cache["Caché de catálogos<br/><i>TTL 5 min · invalida por evento</i>"]
        errores["Manejador de errores<br/><i>traduce códigos a lenguaje de cliente</i>"]

        router --> validador --> orquestador
        orquestador --> cache
        validador --> errores
        orquestador --> errores
    end

    interop["Framework de interoperabilidad"]
    orquestador -->|HTTPS/REST · mTLS| interop

    style bff fill:#E4F2EA,stroke:#008643,stroke-width:2px
    classDef nodo fill:#FFFFFF,stroke:#C4D8CE,color:#1E2A24;
    classDef banco fill:#F2F8F4,stroke:#006332,stroke-width:1.5px,color:#1E2A24;
    class router,validador,orquestador,cache,errores nodo
    class interop banco
:::

### D8 · Seguridad y fronteras de confianza

- Zonas de confianza (internet / DMZ / red interna / nube / terceros) y dónde las cruzan los datos.
- Controles en cada frontera: autenticación, autorización, cifrado, inspección.
- Se construye con Seguridad de la Información en iniciativas tipo A.

| Atributo exigible | Ejemplo |
|---|---|
| Zonas de confianza nombradas (mínimo 3) | `Internet`, `DMZ nube`, `Red interna` |
| Cruces de datos entre zonas explícitos | `App → API Gateway` cruza Internet → DMZ |
| Controles en cada frontera | `WAF`, `mTLS`, `JWT (Entra ID)`, `KMS` |
| **Tabla de certificados y secretos**: ubicación (ruta de vault, nunca el valor), quién los gobierna, vigencia y rotación | Ver tabla complementaria abajo |
| Elaborado con Seguridad (tipo A) declarado en la ficha | `… · con Seguridad de la Información` |
| Ficha del diagrama | `INI-0000 · PRD · 2026-01-01 · Responsable` |

**Ejemplo** (fuente: `skills/diagramas-arquitectura/scripts/d8_fronteras.py` — genera la imagen y la tabla complementaria `D8_fronteras_tabla.md`):

![D8 · Seguridad y fronteras de confianza](img/D8_fronteras.png)

**Tabla complementaria · certificados y secretos**

| Certificado / secreto | Ubicación (ruta de vault, nunca el valor) | Gobernado por | Vigencia | Rotación |
|---|---|---|---|---|
| cert api.banco.com (TLS 1.3) | ACM · vault:/prod/tls | Operaciones TI | 12 meses | Automática, 30 días antes |
| Clave de firma JWT (Entra ID) | Key Vault kv-prod · secrets/jwt-sign | Seguridad de la Información | 24 meses | Manual semestral |
| Certificados mTLS de workload | Vault PKI · pki/prod/issue/app | Operaciones TI | 90 días | Automática |
| Credencial canales-db | Vault KV · kv/prod/canales-db | Operaciones TI | 90 días | Automática |
| Clave KMS cifrado en reposo | AWS KMS · cuenta banco-canales-prod | Seguridad de la Información | Sin vencimiento | Automática anual |

## 5. Mantenimiento: cuándo se actualiza

| Evento | Diagramas que se actualizan |
|---|---|
| Cierre de fase de diseño (P1) | Todos los obligatorios del tipo de iniciativa |
| Cambio aprobado por ADR | Los que el ADR impacta (el ADR lo declara) |
| Cierre de transición (P3) | D3 y D5 quedan como quedó en producción |
| Revisión de vigencia periódica | Verificación ligera: ¿sigue siendo cierto? |
| Cambio de cuenta, ambiente o responsable | D3 de inmediato |

**Anti-patrones que este catálogo prohíbe explícitamente:** diagramas sin nombres reales; diagramas sin fecha ni responsable; capturas de consola como sustituto de diagrama; diagramas C4 nivel 3 de todo el sistema; imágenes sin fuente editable versionada; flujos de datos sin clasificación ni protección declarada.

## 6. Validación automática del contenido exigible

Los scripts parametrizados de Python diagrams (`d2_contenedores.py`, `d3_despliegue.py`, `d5_integracion.py`, `d8_fronteras.py`, `dependencias_apis.py`) incluyen el validador `_exigibles.py`: al generar la imagen imprimen un **checklist** con los atributos exigibles de su tabla y marcan ✓/✗ según la configuración editada. Con `--estricto` el script termina en error si falta algún atributo — pensado para que el pipeline de la iniciativa bloquee diagramas incompletos:

```
Checklist PLT-01 · D3
  ✓ Ficha incluye INI-####
  ✓ Nube con cuenta/suscripción
  ✗ FALTA Ficha con responsable real (no 'Nombre Apellido')
  → 1 atributo(s) exigible(s) faltante(s)
```

Los diagramas mermaid (D1, D4, D6, D7) se revisan contra su tabla exigible en la revisión por pares del DAS (PR), con la misma lista como referencia.

## 7. Sistema de diseño visual

Todos los diagramas del área comparten una identidad: la misma paleta de los entregables Word/Excel (derivada del logo Bancoomeva), una sola fuente tipográfica y estilos por **rol semántico**, no por gusto personal. Los tokens están centralizados y los scripts los importan — **ningún diagrama define colores propios**.

**Paleta**

| Token | Hex | Uso |
|---|---|---|
| Verde corporativo | `#008643` | La solución que construimos/documentamos |
| Verde oscuro | `#006332` | Sistemas internos del banco |
| Rojo corporativo | `#BD1027` | Fronteras críticas de seguridad, datos sensibles (D8) |
| Texto principal | `#1E2A24` | Etiquetas y títulos |
| Tenue | `#5F6E65` | Texto secundario, terceros |
| Línea suave | `#C4D8CE` | Bordes neutros |
| Relleno solución | `#E4F2EA` | Fondo del clúster de la solución |
| Relleno banco | `#F2F8F4` | Fondo de sistemas del banco |
| Relleno externo | `#F5F6F5` | Fondo de terceros (borde punteado) |
| Relleno riesgo | `#FDECEA` | Fondo de zonas críticas |
| AWS | `#E47911` / `#FFF6EC` | Clúster de una cuenta AWS (borde / fondo) |
| Azure | `#0078D4` / `#EAF4FD` | Clúster de una suscripción Azure |
| On-premise | `#8A7F55` / `#F7F4EA` | Clúster de datacenter propio |

**Fuente**: Segoe UI (la de los entregables Word). En Python se fija en `_estilos.py`; en la wiki el texto Mermaid hereda la fuente del navegador.

**Roles semánticos** (misma lectura en cualquier diagrama del banco):

| Rol | Significado | Estilo |
|---|---|---|
| `solucion` | Lo que la iniciativa construye o cambia | Relleno verde claro, borde verde grueso |
| `banco` | Sistemas internos existentes | Relleno verde muy suave, borde verde oscuro |
| `externo` | Terceros, internet, fuera de control del banco | Relleno gris, borde punteado |
| `riesgo` | Zonas críticas de seguridad / datos sensibles | Relleno rojo claro, borde rojo |
| `aws` / `azure` / `onpremise` | Ubicación: cuenta/suscripción propia en esa nube o datacenter | Tinta del proveedor (tabla de paleta) |

**Convención de bordes** — igual de importante que el color:

1. **Todos los recuadros son redondeados**, sin excepción (es parte de la identidad).
2. **Línea continua = dentro del gobierno del banco**: la solución, sistemas internos, nuestras cuentas AWS/Azure y on-premise. Aunque la nube sea de un proveedor, la cuenta es nuestra y la gobernamos.
3. **Línea punteada = fuera del control del banco**: terceros, internet, proveedores, sistemas ajenos. Lo punteado dice "aquí no mandamos nosotros" — clave en D3 y D8.
4. **Usuarios**: internos (funcionarios) con texto verde oscuro; externos (clientes) con texto oscuro neutro.

**Leyenda**: los diagramas **no llevan leyenda embebida** — se probó (v2.4) y rompe el layout y la estética en Graphviz. La convención de colores vive en esta sección y la página de la wiki que publica el diagrama la enlaza con una línea: *"Convención de colores y bordes: PLT-01 §7"*.

**Dónde viven los tokens**

- Python diagrams: `skills/diagramas-arquitectura/scripts/_estilos.py` — los 5 scripts importan `GRAPH_ATTR`, `NODE_ATTR`, `EDGE_ATTR` y `cluster_estilo(rol)`.
- Mermaid: `skills/diagramas-arquitectura/scripts/mermaid/_estilos.mmd` — bloques `classDef`/`style` listos para copiar; las plantillas `.mmd` ya los traen aplicados.
- `sequenceDiagram` (D4) no admite rellenos por participante en la wiki (Mermaid 8.13.9): queda neutro por diseño.

**Regla de cambio de marca**: se ajusta la paleta en `_estilos.py`, `_estilos.mmd` y esta tabla (una decisión, tres lugares), y se regeneran los PNG.

**Reglas de legibilidad** (aprendidas revisando los diagramas en la wiki):

1. **El texto nace grande**: la wiki escala el PNG al ancho de página — título 26pt Semibold, clústeres 15pt, nodos 14pt, aristas 12pt, a 150 dpi (definido en `_estilos.py`; no bajarlo).
2. **Nodo sin clase = error**: en Mermaid, un nodo sin `classDef` sale lavanda (default) y rompe la identidad; todo nodo lleva su clase (`nodo`, `nodoSolucion`, `banco`, `externo`, `riesgo`).
3. **Etiquetas largas se parten**: un path o nombre que supere ~35 caracteres va en dos líneas (`\n` en Python, `<br/>` en Mermaid) para no desbordar su clúster.
4. **Un acento, no un arcoíris**: el rojo `#BD1027` se reserva para riesgo/fronteras; los iconos de producto (nube, motores) ya aportan color — los clústeres y nodos se mantienen en la paleta sobria.
