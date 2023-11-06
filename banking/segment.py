"""
Created on 18.11.2019
__updated__ = "2023-10-10"
@author: Wolfgang Kramer
"""
from datetime import datetime, date, timedelta
from fints.formals import (
    AlgorithmParameterIVName, AlgorithmParameterName,
    BankIdentifier,
    CompressionFunction,
    DateTimeType,
    EncryptionAlgorithm, EncryptionAlgorithmCoded,
    HashAlgorithm,
    IdentifiedRole,
    KeyName, KeyType,
    Language2,
    OperationMode,
    SecurityApplicationArea, SecurityDateTime, SecurityIdentificationDetails, SecurityMethod,
    SecurityProfile, SecurityRole, SignatureAlgorithm, SystemIDStatus, SynchronizationMode,
    UsageEncryption, UserDefinedSignature,
)
from fints.message import FinTSCustomerMessage
from fints.models import SEPAAccount
from fints.segments.auth import HKIDN2, HKVVB3, HKTAN6
from fints.segments.depot import HKWPD5, HKWPD6
from fints.segments.dialog import HKSYN3, HKEND1
from fints.segments.message import HNHBK3, HNHBS1, HNSHK4, HNSHA2, HNVSD1, HNVSK3
from fints.segments.saldo import HKSAL6, HKSAL7
from fints.segments.statement import HKKAZ6, HKKAZ7
from fints.segments.transfer import HKCCS1
from fints.types import SegmentSequence

from banking.declarations import MESSAGE_TEXT, PNS, SYSTEM_ID_UNASSIGNED
from banking.fints_extension import HKCSE1, HKWDU5
from banking.formbuilts import MessageBoxInfo, MessageBoxTermination
from banking.forms import InputTAN


def encrypt(bank, message):
    now = datetime.now()
    plain_segments = message.segments[1:-1]
    del message.segments[1:-1]
    message.segments.insert(
        1,
        HNVSK3(
            security_profile=SecurityProfile(SecurityMethod.PIN, 2),
            security_function=998,
            security_role=SecurityRole.ISS,
            security_identification_details=SecurityIdentificationDetails(
                IdentifiedRole.MS,
                identifier=bank.security_identifier,
            ),
            security_datetime=SecurityDateTime(
                DateTimeType.STS,
                now.date(),
                now.time(),
            ),
            encryption_algorithm=EncryptionAlgorithm(
                UsageEncryption.OSY,
                OperationMode.CBC,
                EncryptionAlgorithmCoded.TWOKEY3DES,
                b'\x00' * 8,
                AlgorithmParameterName.KYE,
                AlgorithmParameterIVName.IVC,
            ),
            key_name=KeyName(
                BankIdentifier(
                    BankIdentifier.COUNTRY_ALPHA_TO_NUMERIC['DE'], bank.bank_code),
                bank.user_id,
                KeyType.V,
                0,
                0,
            ),
            compression_function=CompressionFunction.NULL,
        )
    )
    message.segments[1].header.number = 998
    message.segments.insert(
        2,
        HNVSD1(
            data=SegmentSequence(segments=plain_segments)
        )
    )
    message.segments[2].header.number = 999


def from_to_date(bank):
    if isinstance(bank.to_date, str):
        bank.to_date = date(
            int(bank.to_date[0:4]), int(bank.to_date[5:7]), int(bank.to_date[8:10]))
    if isinstance(bank.from_date, str):
        bank.from_date = date(
            int(bank.from_date[0:4]), int(bank.from_date[5:7]), int(bank.from_date[8:10]))
    if bank.to_date > date.today():
        bank.to_date = date.today()
    if bank.from_date > date.today():
        bank.from_date = date.today()
    if bank.to_date < bank.from_date:
        bank.from_date = bank.to_date
    _latest_date = date.today() - timedelta(bank.storage_period)
    if bank.to_date < _latest_date:
        bank.from_date = _latest_date
        bank.to_date = _latest_date
        if bank.period_message:
            return
        MessageBoxInfo(MESSAGE_TEXT['PERIOD'].format(
            bank.bank_name, bank.bank_code, bank.account_number, bank.account_product_name, _latest_date), bank=bank)
        bank.period_message = True
    else:
        if bank.from_date < _latest_date:
            bank.from_date = _latest_date
            if bank.period_message:
                return
            MessageBoxInfo(MESSAGE_TEXT['PERIOD'].format(
                bank.bank_name, bank.bank_code, bank.account_number, bank.account_product_name, _latest_date), bank=bank)
            bank.period_message = True


def _get_segment(bank, segment_type):

    for seg in [HKKAZ6, HKKAZ7, HKSAL6, HKSAL7, HKWPD5, HKWPD6]:
        if (seg.__name__[2:5] == segment_type
                and seg.__name__[5:6] == str(bank.transaction_versions[segment_type])):
            return seg
    MessageBoxTermination(info=MESSAGE_TEXT['VERSION_TRANSACTION'].format(
        'HK', segment_type, bank.transaction_versions[segment_type]), bank=bank)
    return False  # thread checking


def _sepaaccount(bank):

    return SEPAAccount(iban=bank.iban, bic=bank.bic, accountnumber=bank.account_number,
                       subaccount=bank.subaccount_number, blz=bank.bank_code)


class Segments():
    """
    Segement for use in FinTS Messages
    """

    def segHNHBK(self, bank):
        """
        Segment Nachrichtenkopf
            FINTS Dokument: Schnittstellenspezifikation Formals
            https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Formals_2017-10-06_final_version.pdf
            Nachstehender Kopfteil fuehrt alle Kunden- und Kreditinstitutsnachrichten an.
        """
        message = FinTSCustomerMessage()
        message += HNHBK3(0, 300, bank.dialog_id, bank.message_number)
        return message

    def segHNSHK(self, bank, message):
        """
         Segment Signaturkopf
            FINTS Dokument: Sicherheitsverfahren HBCI
            https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Security_Sicherheitsverfahren_HBCI_Rel_20181129_final_version.pdf

            Der Signaturkopf enthaelt Informationen ueber den damit verbundenen Sicherheitsservice,
            sowie ueber den Absender
        """
        now = datetime.now()
        message += HNSHK4(
            security_profile=SecurityProfile(SecurityMethod.PIN, 2),
            security_function=bank.security_function,
            security_reference=bank.security_reference,
            security_application_area=SecurityApplicationArea.SHM,
            security_role=SecurityRole.ISS,
            security_identification_details=SecurityIdentificationDetails(
                IdentifiedRole.MS,
                identifier=bank.security_identifier,
            ),
            security_reference_number=1,
            security_datetime=SecurityDateTime(
                DateTimeType.STS,
                now.date(),
                now.time(),
            ),
            hash_algorithm=HashAlgorithm(
                usage_hash='1',
                hash_algorithm='999',
                algorithm_parameter_name='1',
            ),
            signature_algorithm=SignatureAlgorithm(
                usage_signature='6',
                signature_algorithm='10',
                operation_mode='16',
            ),
            key_name=KeyName(
                BankIdentifier(
                    BankIdentifier.COUNTRY_ALPHA_TO_NUMERIC['DE'], bank.bank_code),
                bank.user_id,
                KeyType.S,
                0,
                0,
            ),
        )
        return message

    def segHKIND(self, bank, message, user_id=None):
        """
        Segment Identifikation
            FINTS Dokument: Schnittstellenspezifikation Formals
            https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Formals_2017-10-06_final_version.pdf

            Das Identifikations-Segment enthaelt Kontextinformationen, die fuer den gesamten Dialog
            Gueltigkeit haben.
            Anhand dieser Daten wird die Sendeberechtigung des Benutzers geprueft.
            Eine Pruefung der transportmedienspezifischen Kennung des Benutzers erfolgt nicht.
            Falls dem Benutzer die Berechtigung zum Senden weiterer Nachrichten nicht erteilt
            werden kann, ist ein entsprechender Rueckmeldungscode in die Kreditinstitutsantwort
            einzustellen.
            Es steht Kreditinstituten frei, in bestimmten Faellen auf eine Identifizierung des
            Kunden zu verzichten.
            Dies ist zum Beispiel fuer den anonymen Zugang (s.u.) erforderlich, wo mit einem
            Nichtkunden kommuniziert wird.
        """
        if user_id is None:
            # its not a anonymous dialogue: user_id# CUSTOMER_ID_ANONYMOUS
            user_id = bank.user_id
        if bank.system_id == SYSTEM_ID_UNASSIGNED:
            system__id_status = SystemIDStatus.ID_UNNECESSARY
        else:
            system__id_status = SystemIDStatus.ID_NECESSARY
        message += HKIDN2(
            BankIdentifier(
                BankIdentifier.COUNTRY_ALPHA_TO_NUMERIC['DE'], bank.bank_code),
            user_id,
            bank.system_id,
            system_id_status=system__id_status
        )
        return message

    def segHKVVB(self, bank, message):
        """
        Segment Verarbeitungsvorbereitung
            FINTS Dokument: Schnittstellenspezifikation Formals
            https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Formals_2017-10-06_final_version.pdf

            Dieses Segment dient der Uebermittlung von Informationen ueber das Kundensystem,
            mit Hilfe derer das Kreditinstitut individuell auf Anforderungen des Kunden reagieren
        """
        message += HKVVB3(
            bank.bpd_version,
            bank.upd_version,
            Language2.DE,
            bank.product_id,
            '0'
        )
        return message

    def segHKTAN(self, bank, message, segment_name='HKIDN'):
        """
        Segment Geschaeftsvorfall HKTAN6 (starke Kundenauthentifizierung)
            FINTS Dokument: Schnittstellenspezifikation Sicherheitsverfahren PIN/TAN
            https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Security_Sicherheitsverfahren_PINTAN_2018-02-23_final_version.pdf

            Dieser Geschaeftsvorfall dient im Zwei-Schritt-Verfahren dazu, eine Challenge zur
            TAN-Bildung anzufordern und eine TAN zu einem Auftrag zu uebermitteln.
        """
        if bank.task_reference == 'noref':
            bank.task_reference = None
        message += HKTAN6(
            bank.tan_process,
            segment_name,
            task_reference=bank.task_reference,
            further_tan_follows=False
        )
        return message

    def segHKSYN(self, bank, message):
        """
        Segment Synchronisierung
            FINTS Dokument: Schnittstellenspezifikation Formals
            https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Formals_2017-10-06_final_version.pdf

            Bevor ein Benutzer bei Verwendung des PIN/TAN-Verfahrens von einem neuen
            Kundensystem Auftraege erteilen kann, hat er im Wege einer Synchronisierung
            eine Kundensystem-ID fuer dieses System anzufordern.
            Diese ID ist im Folgenden stets anzugeben, wenn der Benutzer von diesem Kundensystem
            aus Nachrichten sendet.
            Wenn eine Synchronisierung der Kundensystem-ID durchgefuehrt wird,  ist das DE
            >Kundensystem-ID< mit dem Wert 0 zu belegen. Das DE >Identifizierung der Partei<
            im Signaturkopf in der DEG <Sicherheitsidentifikation,
            Details< ist mit dem Wert  0 zu belegen.
        """
        message += HKSYN3(SynchronizationMode.NEW_SYSTEM_ID)
        return message

    def segHKKAZ(self, bank, message):
        """
        Segment Kontoumsaetze/Zeitraum
            FINTS Dokument: Schnittstellenspezifikation Messages
                            Multibankfaehige Geschaeftsvorfaelle
            https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Messages_Geschaeftsvorfaelle_2015-08-07_final_version.pdf

            Die Loesung bietet dem Kunden die Moeglichkeit, auf seinem System verlorengegangene
            Buchungen erneut zu erhalten.
            Der maximale Zeitraum, fuer den rueckwirkend Buchungen beim Kreditinstitut gespeichert
            sind, wird in den Bankparameterdaten uebermittelt.

            Kreditinstitutsrueckmeldung:
            Eine Buchungsposition besteht aus einem :61:/:86:-Block eines MT 940Formats.
            Es muss davon unabhaengig immer ein gueltiges MT 940-Format zurueckgemeldet werden,
            d.h. die Felder :20: bis :60: und :62: bis :86: sind obligatorischer Bestandteil
            der Rueckmeldung.
        """
        from_to_date(bank)
        hkkaz = _get_segment(bank, 'KAZ')
        message += hkkaz(
            account=hkkaz._fields['account'].type.from_sepa_account(
                _sepaaccount(bank)),
            all_accounts=False,
            date_start=bank.from_date,
            date_end=bank.to_date
        )
        return message

    def segHKWDU(self, bank, message):
        """
        Segment Depotumsaetze anfordern /Zeitraum
            FINTS Dokument: Schnittstellenspezifikation Messages
                            Multibankfaehige Geschaeftsvorfaelle
            https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Messages_Geschaeftsvorfaelle_2015-08-07_final_version.pdf

            Wertpapierorder stellen nur eine Teilmenge der Depotumsaetze dar.
            Umsaetze koennen auch durch Uebertragungen aus anderen Depots desselben
            oder anderer Kunden, Ausgabe von Gratisaktien, Herabsetzungen des Grundkapitals
            usw. entstehen.

         Kreditinstitutsrueckmeldung:
            Umsatzauskunft: Es ist das S.W.I.F.T.-Format MT 536 in der Version SRG 1998
                            (s. [Datenformate]) einzustellen
        """
        from_to_date(bank)
        hkwdu = HKWDU5
        message += hkwdu(
            account=hkwdu._fields['account'].type.from_sepa_account(
                _sepaaccount(bank)),
            all_accounts=False
        )
        return message

    def segHKWPD(self, bank, message):
        """
        Segment Depotaufstellung anfordern
            FINTS Dokument: Schnittstellenspezifikation Messages
                            Multibankfaehige Geschaeftsvorfaelle
            https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Messages_Geschaeftsvorfaelle_2015-08-07_final_version.pdf

            Die Depotaufstellung kann beliebige Papiere, auch in Fremdwaehrungen, umfassen.

            Kreditinstitutsrueckmeldung:
            Es ist das S.W.I.F.T.-Format MT 535 in der Version SRG 1998 (s. [Datenformate])
            einzustellen.
        """
        hkwpd = _get_segment(bank, 'WPD')
        message += hkwpd(
            account=hkwpd._fields['account'].type.from_sepa_account(
                _sepaaccount(bank))
        )
        return message

    def segHKCCS1(self, bank, message):
        """
        Segment Einzelueberweisung
            FINTS Dokument: Schnittstellenspezifikation Messages
                            Multibankfaehige Geschaeftsvorfaelle
           https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Messages_Geschaeftsvorfaelle_2015-08-07_final_version.pdf

        Fuer Einzelueberweisungsauftraege auf der Basis der pain.001.001.02 ist nur die
         Grouping Option Grouped mit genau einer Einzeltransaktion
         CreditTransferTransactionInformation >CdtTrfTxInf< zugelassen.

        Belegungsrichtlinien
        Kontoverbindung international IBAN und BIC muessen der IBAN in
        DebtorAccount bzw. der BIC in DebtorAgent entsprechen.
        SEPA pain message: Erlaubtes SEPA-Ueberweisungg-Kunde-Bank-Schema lt HISPAS.
        In das Mussfeld RequestedExecutionDate ist 1999-01-01 einzustellen.
        """
        hkcss = HKCCS1
        message += hkcss(
            account=hkcss._fields['account'].type.from_sepa_account(
                _sepaaccount(bank)),
            sepa_descriptor=bank.sepa_descriptor,
            sepa_pain_message=bank.sepa_credit_transfer_data,
        )
        return message

    def segHKCSE1(self, bank, message):
        """
        Segment Terminierte Einzelueberweisung
            FINTS Dokument: Schnittstellenspezifikation Messages
                            Multibankfaehige Geschaeftsvorfaelle
           https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Messages_Geschaeftsvorfaelle_2015-08-07_final_version.pdf

        Fuer Einzelueberweisungsauftraege auf der Basis der pain.001.001.02 ist nur die
         Grouping Option Grouped mit genau einer Einzeltransaktion
         CreditTransferTransactionInformation >CdtTrfTxInf< zugelassen.

        Belegungsrichtlinien
        Kontoverbindung international IBAN und BIC muessen der IBAN in
        DebtorAccount bzw. der BIC in DebtorAgent entsprechen.
        SEPA pain message: Erlaubtes SEPA-Ueberweisungg-Kunde-Bank-Schema lt HISPAS.
        In das Mussfeld RequestedExecutionDate ist der Termin einzustellen.
        """

        hkcse = HKCSE1
        message += hkcse(
            account=hkcse._fields['account'].type.from_sepa_account(
                _sepaaccount(bank)),
            sepa_descriptor=bank.sepa_descriptor,
            sepa_pain_message=bank.sepa_credit_transfer_data,
        )
        return message

    def segHNSHA(self, bank, message):
        """
        Segment Signaturabschluss (PIN)
            FINTS Dokument: Sicherheitsverfahren HBCI
            https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Security_Sicherheitsverfahren_HBCI_Rel_20181129_final_version.pdf

            Der Signaturabschluss stellt die Verbindung mit dem dazugehoerigen Signaturkopf her und
            enthaelt als Validierungsresultat die elektronische Signatur.
        """
        if bank.system_id == SynchronizationMode.NEW_SYSTEM_ID:
            message += HKSYN3(SynchronizationMode.NEW_SYSTEM_ID)
        message += HNSHA2(
            security_reference=bank.security_reference,
            user_defined_signature=UserDefinedSignature(PNS[bank.bank_code])
        )
        return message

    def segHNSHA_TAN(self, bank, message):
        """
        Segment Signaturabschluss (PIN/TAN)
            FINTS Dokument: Sicherheitsverfahren HBCI
            https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Security_Sicherheitsverfahren_HBCI_Rel_20181129_final_version.pdf

            Der Signaturabschluss stellt die Verbindung mit dem dazugehoerigen Signaturkopf her und
            enthaelt als Validierungsresultat die elektronische Signatur.
        """
        if bank.system_id == SynchronizationMode.NEW_SYSTEM_ID:
            message += HKSYN3(SynchronizationMode.NEW_SYSTEM_ID)
        input_tan = InputTAN(bank.bank_code, bank.bank_name)
        message += HNSHA2(
            security_reference=bank.security_reference,
            user_defined_signature=UserDefinedSignature(
                PNS[bank.bank_code], input_tan.tan),
        )
        return message

    def segHNHBS(self, bank, message):
        """
        Segment Nachrichtenabschluss
            FINTS Dokument: Schnittstellenspezifikation Formals
            https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Formals_2017-10-06_final_version.pdf

            Dieses Segment beendet alle Kunden- und Kreditinstitutsnachrichten
        """
        message += HNHBS1(message.segments[0].message_number)
        encrypt(bank, message)
        message.segments[0].message_size = len(message.render_bytes())
        bank.message_number += 1
        return message

    def segHNHBSnoencrypt(self, bank, message):
        """
        Segment Nachrichtenabschluss
            FINTS Dokument: Schnittstellenspezifikation Formals
            https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Formals_2017-10-06_final_version.pdf

            Dieses Segment beendet alle Kunden- und Kreditinstitutsnachrichten
            ohne Verschluesselung
        """
        message += HNHBS1(message.segments[0].message_number)
        message.segments[0].message_size = len(message.render_bytes())
        bank.message_number += 1
        return message

    def segHKEND(self, bank, message):
        """
        Segment Dialogende
            FINTS Dokument: Schnittstellenspezifikation Formals
            https://www.hbci-zka.de/dokumente/spezifikation_deutsch/fintsv3/FinTS_3.0_Formals_2017-10-06_final_version.pdf

            Die Nachricht muss signiert und verschluesselt werden (Ausnahmen s. Kap. C.4.1)
            und wird mit einer Standard-Kreditinstitutsnachricht beantwortet.
            Die Nachricht ist von demjenigen Benutzer zu signieren, der auch die
            Dialoginitialisierung signiert hat.
        """
        message += HKEND1(bank.dialog_id)
        return message
