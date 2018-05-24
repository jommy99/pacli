import fire
import pypeerassets as pa
from pacli.provider import provider
from pacli.config import Settings
from pacli.keystore import init_keystore
from pacli.tui import print_deck_info, print_deck_list
from pacli.tui import print_card_list
import json


def cointoolkit_verify(hex: str) -> str:
    '''tailor cointoolkit verify URL'''

    base_url = 'https://indiciumfund.github.io/cointoolkit/'
    if provider.network == "peercoin-testnet":
        mode = "mode=peercoin_testnet"
    if provider.network == "peercoin":
        mode = "mode=peercoin"

    return base_url + "?" + mode + "&" + "verify=" + hex


class Address:

    '''my personal address'''

    def show(self, pubkey: bool=False, privkey: bool=False, wif: bool=False):
        '''print address, pubkey or privkey'''

        if pubkey:
            return Settings.key.pubkey
        if privkey:
            return Settings.key.privkey
        if wif:
            return Settings.key.wif

        return Settings.key.address

    @classmethod
    def balance(self):

        return float(provider.getbalance(Settings.key.address))


class Deck:

    @classmethod
    def list(self):
        '''find all valid decks and list them.'''

        decks = pa.find_all_valid_decks(provider, Settings.deck_version,
                                        Settings.production)

        print_deck_list(decks)

    @classmethod
    def find(self, key):
        '''
        Find specific deck by key, with key being:
        <id>, <name>, <issuer>, <issue_mode>, <number_of_decimals>
        '''

        decks = pa.find_all_valid_decks(provider,
                                        Settings.deck_version,
                                        Settings.production)
        print_deck_list((d for d in decks if key in d.__dict__.values()))

    @classmethod
    def info(self, deck_id):
        '''display deck info'''

        deck = pa.find_deck(provider, deck_id, Settings.deck_version,
                            Settings.production)
        print_deck_info(deck)

    @classmethod
    def new(self, name: str, number_of_decimals: int, issue_mode: int,
            asset_specific_data: bytes=None):
        '''create a new deck.'''

        network = Settings.network
        production = Settings.production
        version = Settings.deck_version

        new_deck = pa.Deck(name, number_of_decimals, issue_mode, network,
                           production, version, asset_specific_data)

        return new_deck

    @classmethod
    def spawn(self, verify=False, **kwargs):
        '''prepare deck spawn transaction'''

        deck = self.new(**kwargs)

        spawn = pa.deck_spawn(provider=provider,
                              inputs=provider.select_inputs(Settings.key.address, 0.02),
                              deck=deck,
                              change_address=Settings.change
                              )

        if verify:
            return cointoolkit_verify(spawn.hexlify())  # link to cointoolkit - verify

        return spawn.hexlify()

    @classmethod
    def encode(self, json: bool=False, **kwargs) -> str:
        '''compose a new deck and print out the protobuf which
           is to be manually inserted in the OP_RETURN of the transaction.'''

        if json:
            return self.new(**kwargs).metainfo_to_dict

        return self.new(**kwargs).metainfo_to_protobuf.hex()

    @classmethod
    def decode(self, protobuf: str) -> dict:
        '''decode deck protobuf'''

        return pa.parse_deckspawn_metainfo(bytes.fromhex(protobuf), Settings.deck_version)

    def issue_modes(self):

        im = tuple({mode.name: mode.value} for mode_name, mode in pa.IssueMode.__members__.items())

        print(json.dumps(im, indent=1, sort_keys=True))

    def checksum(self, deck_id: str) -> bool:
        '''check if deck balances are in order'''

        raise NotImplementedError


class Card:

    '''card information and manipulation'''

    @classmethod
    def list(self, deckid: str):
        '''list the valid cards on this deck'''

        deck = pa.find_deck(provider, deckid,
                            Settings.deck_version,
                            Settings.production)

        try:
            cards = pa.find_card_transfers(provider, deck)
            print_card_list(cards)
        except pa.exceptions.EmptyP2THDirectory as err:
            return err

    def balances(self, deckid):
        '''list card balances on this deck'''
        raise NotImplementedError

    @classmethod
    def new(self, deckid: str, receiver: list=None,
            amount: list=None, asset_specific_data: str=None) -> pa.CardTransfer:
        '''fabricate a new card transaction
        * deck_id - deck in question
        * receiver - list of receivers
        * amount - list of amounts to be sent, must be float
        '''

        production = Settings.production
        version = Settings.deck_version
        deck = pa.find_deck(provider, deckid, version, production)

        card = pa.CardTransfer(deck, receiver, amount, version, asset_specific_data)

        return card

    @classmethod
    def transfer(self, deckid: str, receiver: list=None, amount: list=None,
                 asset_specific_data: str=None, verify=False) -> str:
        '''prepare CardTransfer transaction'''

        card = self.new(deckid, receiver, amount, asset_specific_data)

        issue = pa.card_transfer(provider=provider,
                                 inputs=provider.select_inputs(Settings.key.address, 0.02),
                                 card=card,
                                 change_address=Settings.change
                                 )

        if verify:
            return cointoolkit_verify(issue.hexlify())  # link to cointoolkit - verify

        return issue.hexlify()

    @classmethod
    def burn(self, deckid: str, receiver: list=None, amount: list=None,
             asset_specific_data: str=None, verify=False) -> str:
        '''wrapper around self.transfer'''

        return self.transfer(deckid, receiver, amount, asset_specific_data, verify)

    @classmethod
    def issue(self, deckid: str, receiver: list=None, amount: list=None,
              asset_specific_data: str=None, verify=False) -> str:
        '''Wrapper around self.tranfer'''

        return self.transfer(deckid, receiver, amount, asset_specific_data, verify)

    @classmethod
    def encode(self, deckid: str, receiver: list=None, amount: list=None,
               asset_specific_data: str=None, json: bool=False) -> str:
        '''compose a new card and print out the protobuf which
           is to be manually inserted in the OP_RETURN of the transaction.'''

        card = self.new(deckid, receiver, amount, asset_specific_data)

        if json:
            return card.metainfo_to_dict

        return card.metainfo_to_protobuf.hex()

    @classmethod
    def decode(self, protobuf: str) -> dict:
        '''decode card protobuf'''

        return pa.parse_card_transfer_metainfo(bytes.fromhex(protobuf),
                                               Settings.deck_version)


def main():

    init_keystore()

    fire.Fire({
        'deck': Deck(),
        'card': Card(),
        'address': Address()
        })


if __name__ == '__main__':
    main()
