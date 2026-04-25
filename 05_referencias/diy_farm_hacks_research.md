# 🛠️ Proyectos DIY (Hazlo Tú Mismo) para Granja Cabral

En el "primer mundo", las granjas avícolas gastan cientos de miles de dólares en máquinas industriales (como las clasificadoras *Moba* o silos inteligentes *BigFarmNet*). 

Sin embargo, comunidades de *Makers* en **Instructables**, **GitHub** y **Thingiverse** han logrado replicar (hackear) esta misma tecnología usando microcontroladores de $5 dólares (Arduino/ESP32), piezas impresas en 3D y tubos de PVC. 

Aquí están los mejores proyectos DIY que Alejandro puede construir en su casa y llevar a la granja por menos de $100 USD.

---

## 🥚 1. Clasificadora de Huevos Automática (DIY Egg Grader)
**El problema:** Clasificar 2.130 huevos al día a mano en tamaños (A, B, S, Jumbo) es lento y propenso a error humano. Las máquinas clasificadoras industriales cuestan más de $20,000 USD.

**La Solución Hacker (Arduino + Impresión 3D):**
Existen múltiples proyectos *Open Source* en Instructables y YouTube para armar una balanza clasificadora dinámica.
- **El Cerebro:** Un Arduino Nano ($5 USD).
- **El Sensor:** Una Celda de Carga (Load Cell) de 1Kg conectada a un amplificador **HX711** ($3 USD). Es una balanza digital híper precisa.
- **La Mecánica:** Servomotores básicos ($4 USD) y una estructura impresa en 3D (disponible en Thingiverse).
- **Cómo funciona:** El huevo rueda por una rampa de PVC hacia la balanza. El Arduino lo pesa en milisegundos. Si pesa más de 65g (Tamaño A), el Arduino mueve un servomotor que abre una "puerta" y el huevo cae suavemente al canal de la caja "A". Si pesa 75g+ (Jumbo), abre la compuerta final.
- **Costo total:** ~$40 USD.

## 🌽 2. Silo de Alimento Inteligente (Smart Feed Silo)
**El problema:** Laura no sabe exactamente cuántos gramos comen las gallinas por día a menos que el operario cuente las bolsas manualmente.

**La Solución Hacker (ESP32 + Celdas de Carga Industriales):**
Las granjas de primer mundo tienen las "patas" de sus silos apoyadas en balanzas gigantes para saber a cada segundo cuánto alimento queda.
- **El Hack:** Alejandro puede comprar 4 "Celdas de Carga" (Load Cells) de 500Kg cada una y colocarlas debajo de las patas del depósito de alimento principal de la granja.
- **El Cerebro:** Un **ESP32** (Un microcontrolador con WiFi integrado de $6 USD). 
- **Cómo funciona:** El ESP32 lee el peso del silo constantemente. Alejandro programa el ESP32 para enviar los datos a un Google Sheet cada hora. Si el peso baja drásticamente o se acerca a 0, el ESP32 hace una petición HTTP (Webhook) a Make.com y le envía un mensaje automático al WhatsApp de Laura: *"Quedan menos de 100Kg de alimento"*.
- **Costo total:** ~$60 USD por la electrónica.

## 💧 3. Medidor Digital de Flujo de Agua (Detección de Enfermedades)
**El problema:** La primera señal de que las 2.500 gallinas están enfermas (ej. Bronquitis o estrés por calor) es que dejan de tomar agua, días antes de que mueran o dejen de poner huevos.

**La Solución Hacker:**
- **El Hardware:** Un sensor de flujo de agua (Water Flow Meter YF-S201) de $8 USD insertado directamente en el tubo central de PVC que alimenta los bebederos de *niple* del galpón.
- **El Cerebro:** Un Arduino o ESP32 que cuente los litros de agua consumidos.
- **Cómo funciona:** Si el consumo histórico del galpón es de 500 litros diarios, y un martes a mediodía el Arduino detecta que solo han tomado 100 litros, dispara una alerta inmediata al celular: *"Alerta Roja: Consumo de agua 60% por debajo de lo normal. Posible enfermedad o caño roto."*

## 🚪 4. Cortinas/Ventilación Termostática Autónoma
**El problema:** Si hace 35°C de repente y el peón no está, las aves sufren estrés térmico.

**La Solución Hacker (Instructables):**
- **Mecánica:** Un motor de limpiaparabrisas viejo de auto (12V) o un actuador lineal ($30 USD).
- **Cerebro y Sensor:** Un módulo relé conectado al sensor de temperatura Tuya WiFi.
- **Cómo funciona:** Se ata el actuador a la soga de las cortinas laterales del galpón (si las tiene) o al interruptor de los ventiladores extractores grandes. Si la temperatura pasa los 28°C, se cierran los relés, encendiendo los ventiladores y bajando las cortinas automáticamente sin intervención humana.

---

### 💻 Conclusión para Alejandro
El Ecosistema *Open Source* es el mejor amigo de la Granja Cabral. En lugar de pagar miles de dólares a empresas de agrotecnología, Alejandro solo necesita:
1. Una impresora 3D (Ender 3 - $150 USD) para imprimir las piezas de Thingiverse.
2. Saber soldar 4 cables a una placa ESP32 o Arduino.
3. El lenguaje de programación de Arduino (C++) para enviar los datos del hardware directamente a la arquitectura de Google Sheets que ya diseñamos.
