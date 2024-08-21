# Betrokkenen/rollen with authentication context

Example API calls with required fields and dummy data, the focus is on the shape of
`authenticatieContext`.

## DigiD / Without mandate

### DigiD - initiator

```http
POST /zaken/api/v1/rollen
Content-Type: application/json

{
  "zaak": "http://example.com",
  "betrokkeneType": "natuurlijk_persoon",
  "roltype": "http://example.com/roltype-initiator",
  "roltoelichting": "Created zaak",
  "betrokkeneIdentificatie": {
    "inpBsn": "123456782"
  },
  "authenticatieContext": {
    "source": "digid",
    "levelOfAssurance": "urn:oasis:names:tc:SAML:2.0:ac:classes:MobileTwoFactorContract"
  }
}
```

### DigiD - belanghebbende

```http
POST /zaken/api/v1/rollen
Content-Type: application/json

{
  "zaak": "http://example.com",
  "betrokkeneType": "natuurlijk_persoon",
  "roltype": "http://example.com/roltype-belanghebbende",
  "roltoelichting": "Voogd",
  "betrokkeneIdentificatie": {
    "inpBsn": "123456782"
  },
  "authenticatieContext": null
}
```

## DigiD / With mandate

### DigiD - initiator

The authorizee is the initiator of the case (cleared up from VNG github), the representee
is a "belanghebbende".

```http
POST /zaken/api/v1/rollen
Content-Type: application/json

{
  "zaak": "http://example.com",
  "betrokkeneType": "natuurlijk_persoon",
  "roltype": "http://example.com/roltype-initiator",
  "roltoelichting": "Created zaak",
  "indicatieMachtiging": "gemachtigde",
  "betrokkeneIdentificatie": {
    "inpBsn": "123456782"
  },
  "authenticatieContext": {
    "source": "digid",
    "levelOfAssurance": "urn:oasis:names:tc:SAML:2.0:ac:classes:MobileTwoFactorContract"
    "representee": {
      "identifierType": "bsn",
      "identifier": "111222333"
    },
    "mandate": {
      "services": [
        {"id": "5628edbd-333e-460d-8a69-8f083b8cf1b8"}
      ]
    }
  }
}
```

### DigiD - belanghebbende

```http
POST /zaken/api/v1/rollen
Content-Type: application/json

{
  "zaak": "http://example.com",
  "betrokkeneType": "natuurlijk_persoon",
  "roltype": "http://example.com/roltype-belanghebbende",
  "roltoelichting": "Voogd",
  "indicatieMachtiging": "machtiginggever",
  "betrokkeneIdentificatie": {
    "inpBsn": "111222333"
  },
  "authenticatieContext": null
}
```

## DigiD // Query patterns

1. Show me my cases:

    - show zaken WHERE -- cases opened for myself
        betrokkeneIdentificatie = :ownBsn
        AND rol.omschrijvingGeneriek = initiator
        AND rol.indicatieMachtiging = none -- exclude myself as authorizee

    - show zaken WHERE -- cases opened by an authorizee on my behalf
        betrokkeneIdentificatie = :ownBsn
        AND rol.omschrijvingGeneriek = belanghebbende
        AND rol.indicatieMachtiging = machtiginggever

    - show zaken WHERE -- potential future thing: exclude based on LOA
        betrokkeneIdentificatie = :ownBsn
        AND rol.omschrijvingGeneriek = initiator
        AND rol.indicatieMachtiging = none -- exclude myself as authorizee
        AND rol.authContext.loa <= :currentLoa

2. Show me the cases where I represent someone

    - show zaken WHERE
        betrokkeneIdentificatie = :ownBsn
        AND rol.omschrijvingGeneriek = initiator
        AND rol.indicatieMachtiging = gemachtigde
        -- info available when logging in via DigiD machtigen
        AND rol.authContext.loa <= :currentLoa  -- optional - up to portal
        AND rol.authContext.representee <= :bsnRepresentee -- optional - up to portal

## eHerkenning / Without mandate

### eHerkenning - initiator (no branch)

```http
POST /zaken/api/v1/rollen
Content-Type: application/json

{
  "zaak": "http://example.com",
  "betrokkeneType": "niet_natuurlijk_persoon",
  "roltype": "http://example.com/roltype-initiator",
  "roltoelichting": "Created zaak",
  "contactpersoonRol": {
    "naam": "acting subject name"
  },
  "betrokkeneIdentificatie": {
    "innNnpId": "999999999"
  },
  "authenticatieContext": {
    "source": "eherkenning",
    "levelOfAssurance": "urn:etoegang:core:assurance-class:loa2plus",
    "actingSubject": "4B75A0EA107B3D36C82FD675B5B78CC2F181B22E33D85F2D4A5DA63452EE3018@2D8FF1EF10279BC2643F376D89835151"
  }
}
```

### eHerkenning - initiator (branch)

```http
POST /zaken/api/v1/rollen
Content-Type: application/json

{
  "zaak": "http://example.com",
  "betrokkeneType": "vestiging",
  "roltype": "http://example.com/roltype-initiator",
  "roltoelichting": "Created zaak",
  "contactpersoonRol": {
    "naam": "acting subject name"
  },
  "betrokkeneIdentificatie": {
    "kvkNummer": "12345678",
    "vestigingsNummer": "123456789012"
  },
  "authenticatieContext": {
    "source": "eherkenning",
    "levelOfAssurance": "urn:etoegang:core:assurance-class:loa2plus",
    "actingSubject": "4B75A0EA107B3D36C82FD675B5B78CC2F181B22E33D85F2D4A5DA63452EE3018@2D8FF1EF10279BC2643F376D89835151"
  }
}
```

## eHerkenning / With mandate (bewindvoering)

### Initiator (branch, (or not, not really relevant for auth context))

### eHerkenning - initiator (branch)

```http
POST /zaken/api/v1/rollen
Content-Type: application/json

{
  "zaak": "http://example.com",
  "betrokkeneType": "vestiging",
  "roltype": "http://example.com/roltype-initiator",
  "roltoelichting": "Created zaak",
  "contactpersoonRol": {
    "naam": "acting subject name"
  },
  "indicatieMachtiging": "gemachtigde",
  "betrokkeneIdentificatie": {
    "kvkNummer": "12345678",
    "vestigingsNummer": "123456789012"
  },
  "authenticatieContext": {
    "source": "eherkenning",
    "levelOfAssurance": "urn:etoegang:core:assurance-class:loa2plus",
    "representee": {
      "identifierType": "bsn",
      "identifier": "111222333"
    },
    "actingSubject": "4B75A0EA107B3D36C82FD675B5B78CC2F181B22E33D85F2D4A5DA63452EE3018@2D8FF1EF10279BC2643F376D89835151"
    "mandate": {
      "role": "bewindvoerder",
      "services": [{
        "id": "urn:etoegang:DV:00000001002308836000:services:9113",
        "uuid": "34085d78-21aa-4481-a219-b28d7f3282fc"
      }]
    }
  }
}
```

### eHerkenning - belanghebbende

```http
POST /zaken/api/v1/rollen
Content-Type: application/json

{
  "zaak": "http://example.com",
  "betrokkeneType": "natuurlijk_persoon",
  "roltype": "http://example.com/roltype-belanghebbende",
  "roltoelichting": "Persoon waarover bewind gevoerd wordt",
  "indicatieMachtiging": "machtiginggever",
  "betrokkeneIdentificatie": {
    "inpBsn": "111222333"
  },
  "authenticatieContext": null
}
```

## Validation rules

If `representee` is provided in auth context, then:
    * `indicatieMachtiging` **MUST** be set to "gemachtigde"
    * `mandate` **MUST** be provided in auth context

## What about other betrokkene types:

* organisatorische_eenheid: auth context not meaningful + is internal
* medewerker: auth context not meaningful + is internal
