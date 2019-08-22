# Architectuur

De architectuur van **Open Zaak** heeft ten doel om performance, stabiliteit en data-integriteit te verbeteren ten op zichte van de [referentie implementaties van VNG Realisatie](https://github.com/VNG-Realisatie/gemma-zaken). De architectuur blijft trouw aan de [Common Ground](https://commonground.nl/) principes.

**Open Zaak** combineert de API's voor Zaakgericht werken die nauw met elkaar samenwerken in één product. Hierdoor kan een flinke performance winst worden behaald aangezien gerelateerde objecten, zoals het BESLUIT bij een ZAAK, niet meer over het netwerk opgehaald hoeven te worden. Dit uitgangspunt zorgt ook voor data integriteit op database niveau in plaats van op service niveau.

Daarnaast implementeerd **Open Zaak** een caching strategie om ook performance winst te behalen bij het raadplegen van externe API's. Data integriteit kan met externe API's niet op database niveau worden afgedwongen. Data integriteit waarbij gebruik wordt gemaakt van externe API's zal dus nog zo veel mogelijk op service niveau worden afgedwongen.

**Open Zaak** kan dus omgaan met zowel de eigen API's als externe API's, ook als deze API's ook door **Open Zaak** worden aangeboden. Zo kan een ZAAK in **Open Zaak**, beschikbaar via de Zaken API van **Open Zaak**, een DOCUMENT hebben in de Documenten API van een andere aanbieder. De enige vereiste is dat de API's voor Zaakgericht werken voldoen aan [VNG standaarden voor API's voor Zaakgericht werken](https://zaakgerichtwerken.vng.cloud/).

Er worden, in lijn met de [Common Ground principes](https://www.vngrealisatie.nl/index.php/roadmap/common-ground), geen kopieën van bronnen worden gemaakt en **Open Zaak** bevat alleen de gegevens- en servicelaag, waardoor data gescheiden blijft van applicaties. 
