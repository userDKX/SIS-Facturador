# Firma del comprobante (XMLDSig)

Este es el lado del proyecto que más cuesta entender bien y donde más cosas
sutiles te pueden tirar el envío con un error que no dice nada útil. Vale la
pena leerlo entero antes de tocar `pe_invoicing/signer/xmldsig.py`.

## Contexto: XMLDSig vs XAdES-BES

Hay dos estándares de firma XML que vas a ver mencionados en cualquier doc
de facturación electrónica:

- **XMLDSig** (W3C 2002, actualizado 2008): la firma básica.
  `<ds:Signature>` con `SignedInfo` (referencias + algoritmos),
  `SignatureValue` (la firma RSA propiamente), y `KeyInfo` (cómo verificar
  la firma — típicamente embebido el cert X.509).
- **XAdES-BES** (ETSI TS 101 903): superset de XMLDSig que agrega metadata
  firmada en `<xades:SignedSignatureProperties>`: timestamp del firmante,
  política de firma, role del firmante, etc. Es lo que muchos proyectos
  europeos y algunos sudamericanos exigen.

Cuando empezamos este proyecto asumimos que SUNAT pedía XAdES-BES porque
así lo hacen otros países. **No es así.** SUNAT acepta y verifica XMLDSig
puro, sin las extensiones XAdES. Si revisas el manual del emisor del SEE,
nunca menciona XAdES. Si lees el código de Greenter (la implementación de
referencia en PHP), tampoco firma XAdES.

Mandar XAdES no rompe nada — SUNAT lo procesa porque el XAdES es válido
como XMLDSig (los nodos extra van dentro de `Object`). Pero es trabajo y
complejidad gratis. Acá firmamos XMLDSig nomás.

## Algoritmos exactos

Los tres ejes del XMLDSig:

| Eje                     | Valor que usamos                                | URI                                                              |
|-------------------------|-------------------------------------------------|------------------------------------------------------------------|
| `SignatureMethod`       | RSA con SHA-256                                 | `http://www.w3.org/2001/04/xmldsig-more#rsa-sha256`              |
| `DigestMethod`          | SHA-256                                         | `http://www.w3.org/2001/04/xmlenc#sha256`                        |
| `CanonicalizationMethod`| Exclusive C14N 1.0                              | `http://www.w3.org/2001/10/xml-exc-c14n#`                        |
| `Transform` de la `Reference` | enveloped-signature                       | `http://www.w3.org/2000/09/xmldsig#enveloped-signature`          |

SUNAT hace tiempo aceptaba SHA-1 además de SHA-256. Hoy mejor usar SHA-256
de frente — los certs nuevos emitidos por RENIEC son RSA 2048 y SHA-256 es
compatible.

**Por qué Exclusive C14N y no Inclusive:** la canonicalización inclusive
(C14N) hereda los namespaces declarados en ancestros del elemento firmado.
En un UBL eso es un drama porque el root tiene namespaces que no usamos
todos en los hijos, y la firma se vuelve frágil ante reformateos. Exclusive
C14N solo incluye los namespaces que el elemento usa de verdad.

**Por qué `enveloped-signature`:** la firma vive *dentro* del documento que
firma. La transform le dice al verificador "calcula el digest del documento
sacando la propia firma". Sin esto, el digest cambiaría al insertar la
firma y la verificación fallaría siempre.

## El gotcha grande: dónde tiene que vivir `<ds:Signature>`

Por defecto, `signxml.XMLSigner` con `method=enveloped` inserta la firma
como **último hijo del root**. En un UBL eso quedaría así:

```xml
<Invoice xmlns="...">
  <ext:UBLExtensions>...</ext:UBLExtensions>
  <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
  ...
  <cac:InvoiceLine>...</cac:InvoiceLine>
  <ds:Signature>...</ds:Signature>     ← signxml lo deja acá
</Invoice>
```

SUNAT rechaza eso. Exige que la firma viva específicamente acá:

```xml
<Invoice xmlns="...">
  <ext:UBLExtensions>
    <ext:UBLExtension>
      <ext:ExtensionContent>
        <ds:Signature>...</ds:Signature>     ← acá tiene que ir
      </ext:ExtensionContent>
    </ext:UBLExtension>
  </ext:UBLExtensions>
  ...
</Invoice>
```

La solución que aplica `pe_invoicing/signer/xmldsig.py`: firmar normal (signxml deja
la firma fuera), después usar `lxml` para mover el elemento al lugar
correcto. La transform `enveloped-signature` hace que el digest se haya
calculado sin contar la firma misma, así que mover el `ds:Signature` no
invalida nada.

```python
signed_root = signer.sign(root, key=bundle.key_pem, cert=bundle.cert_pem)

signature = signed_root.find(f"{{{NS_DS}}}Signature")
signature.set("Id", SIGNATURE_ID)        # SUNAT espera Id="SignatureSP"

ext_content = signed_root.find(
    f"{{{NS_EXT}}}UBLExtensions/{{{NS_EXT}}}UBLExtension/{{{NS_EXT}}}ExtensionContent"
)
signed_root.remove(signature)
ext_content.append(signature)
```

El `Id="SignatureSP"` es porque la plantilla UBL referencia esa firma desde
`<cac:Signature><cac:DigitalSignatureAttachment><cac:ExternalReference><cbc:URI>#SignatureSP</cbc:URI>`.
La URI tiene que matchear el Id.

## URI de la `Reference` vacío

En XMLDSig, la `Reference` apunta al recurso que se firma. SUNAT usa el
URI vacío:

```xml
<ds:Reference URI="">
  <ds:Transforms>
    <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
  </ds:Transforms>
  ...
</ds:Reference>
```

URI vacío significa "el documento entero". Combinado con la transform
enveloped-signature, eso es: "calcula el digest del documento entero
quitando la firma". Es el modo correcto cuando la firma está embebida en
lo que firma.

## El cert X.509 va en `KeyInfo`

```xml
<ds:KeyInfo>
  <ds:X509Data>
    <ds:X509Certificate>MIIE...base64...</ds:X509Certificate>
  </ds:X509Data>
</ds:KeyInfo>
```

Es el cert PEM sin los headers `-----BEGIN CERTIFICATE-----`, en una sola
línea base64. `signxml` lo arma solo cuando le pasas `cert=cert_pem` en
`signer.sign()`.

SUNAT verifica que el cert:

- Sea RSA 2048 o más (ya nadie pone menos).
- Esté vigente (`not_valid_before <= now <= not_valid_after`).
- Sea el mismo que registraste en el formulario del SEE-DSC (compara por
  serial number).
- Esté emitido por una CA que SUNAT reconoce (la más común en Perú es
  ECEP-RENIEC; también acepta otras como Camerfirma, Llama.pe, etc.).

## El otro gotcha: CDATA + Jinja2 = double encoding

Versión inicial de la plantilla tenía:

```jinja
<cbc:Description><![CDATA[{{ line.descripcion }}]]></cbc:Description>
```

La idea era escapar los caracteres especiales (`&`, `<`, `>`) en
descripciones de items metiéndolos en CDATA. Pero Jinja2 con `autoescape`
(activado por defecto en `select_autoescape`) ya escapa el contenido a
`&amp;` antes de meterlo en el template. Resultado: el `&` original termina
como `&amp;amp;` en el XML.

Lo correcto es dejar que Jinja maneje el escape y no usar CDATA:

```jinja
<cbc:Description>{{ line.descripcion }}</cbc:Description>
```

`lxml` después re-serializa el DOM y el escaping queda consistente.

## Cómo validar la firma localmente

`scripts/verify_cert.py` carga el cert, firma un UBL de muestra, y verifica
la firma sin tocar SUNAT. Si esto pasa, la cadena de firma está bien:

```bash
make verify-cert
```

Si quieres validar la firma con una herramienta independiente, `xmlsec1`
es el CLI estándar:

```bash
# Linux / macOS
xmlsec1 verify --enabled-key-data x509 firmado.xml
```

(En Windows hay binarios de `xmlsec1` por libxmlsec, o se puede usar dentro
de WSL.)

## Snippet del XML firmado real

Esto es la parte de `<ext:UBLExtensions>` de un comprobante real (cert y
digest anonimizados):

```xml
<ext:UBLExtensions>
  <ext:UBLExtension>
    <ext:ExtensionContent>
      <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="SignatureSP">
        <ds:SignedInfo>
          <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
          <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
          <ds:Reference URI="">
            <ds:Transforms>
              <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
            </ds:Transforms>
            <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
            <ds:DigestValue>XXXX...sha256_del_doc_sin_firma...XXXX</ds:DigestValue>
          </ds:Reference>
        </ds:SignedInfo>
        <ds:SignatureValue>YYYY...firma_rsa_sha256_base64...YYYY</ds:SignatureValue>
        <ds:KeyInfo>
          <ds:X509Data>
            <ds:X509Certificate>MIIE...cert_x509_base64...</ds:X509Certificate>
          </ds:X509Data>
        </ds:KeyInfo>
      </ds:Signature>
    </ext:ExtensionContent>
  </ext:UBLExtension>
</ext:UBLExtensions>
```

## Referencias

- [W3C XMLDSig Recommendation](https://www.w3.org/TR/xmldsig-core/)
- [Exclusive C14N](https://www.w3.org/TR/xml-exc-c14n/)
- [`signxml` docs](https://xml-security.github.io/signxml/)
- [Manual del Programador SEE-DSC](https://cpe.sunat.gob.pe/sites/default/files/inline-files/Manual%20del%20Programador.pdf)
  (la versión vigente la publica SUNAT en https://cpe.sunat.gob.pe)
- [Greenter](https://github.com/giansalex/greenter) — la implementación de
  referencia en PHP. Útil para contrastar decisiones cuando algo no está
  claro en la doc oficial.
