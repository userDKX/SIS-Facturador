# Atribuciones del bundle de XSDs

Este directorio incluye obras de terceros redistribuidas con `sunat-py`
para validacion XSD client-side de XML UBL.

## OASIS UBL 2.1 (subdir `ubl-2.1/`)

Copyright © OASIS Open 2013. All Rights Reserved.

Los XSDs UBL 2.1 son parte del estandar Universal Business Language
Version 2.1, ratificado como OASIS Standard el 04-Nov-2013. Se
redistribuyen bajo los terminos de la OASIS Open Intellectual Property
Rights (IPR) Policy, preservando copyright y atribuciones originales.

Texto completo de la licencia y politica IPR de OASIS:
<https://www.oasis-open.org/policies-guidelines/ipr/>

Source de la version redistribuida aqui:
<https://docs.oasis-open.org/ubl/os-UBL-2.1/xsd/>

## SUNAT UBL 2.0 + extensiones peruanas (subdir `sunat-1.0/`)

Los XSDs de comprobantes peruanos (`UBLPE-Retention-1.0.xsd`,
`UBLPE-Perception-1.0.xsd`, `UBLPE-SummaryDocuments-1.0.xsd`,
`UBLPE-VoidedDocuments-1.0.xsd`, `UBLPE-ApplicationResponse-1.0.xsd`,
`UBLPE-SunatAggregateComponents-*.xsd`) y los archivos UBL 2.0 base que
los soportan son artefactos publicos emitidos por la Superintendencia
Nacional de Aduanas y de Administracion Tributaria del Peru (SUNAT)
como parte de la regulacion del Sistema de Emision Electronica (SEE)
de Comprobantes de Pago.

Distribucion original (URL estable verificada, 28/02/2022):
<https://cpe.sunat.gob.pe/sites/default/files/inline-files/Archivos%20XSD%20%281%29.zip>

Portal CPE general:
<https://cpe.sunat.gob.pe/>

Estos XSDs no llevan licencia explicita: se publican como anexos
tecnicos de Resoluciones de Superintendencia (norma juridica peruana)
que regulan el formato obligatorio de los comprobantes de pago
electronicos. Se redistribuyen aqui sin modificar el contenido
normativo.

## Modificaciones aplicadas

Los archivos se redistribuyen sin modificar contenido. `targetNamespace`
y declaraciones intactas. Lo unico que cambia es la organizacion en
disco: el script de refresh aplana el layout del ZIP SUNAT
(`Archivos XSD/2.0/{maindoc,common}/`) en `sunat-1.0/{maindoc,common}/`
para que `lxml.etree.XMLSchema` resuelva imports relativos contra el
filesystem local. Los `xs:import schemaLocation="..."` adentro de los
XSDs no se tocan.
