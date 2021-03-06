import re

from spike.model import db
from shlex import shlex

from spike.model.naxsi_rules import NaxsiRules
from flask import url_for


class NaxsiWhitelist(db.Model):
    __bind_key__ = 'rules'
    __tablename__ = 'naxsi_whitelist'

    id = db.Column(db.Integer, primary_key=True)
    wid = db.Column(db.String, nullable=False)
    mz = db.Column(db.String(1024), nullable=False)
    negative = db.Column(db.Integer, nullable=False, server_default='0')
    active = db.Column(db.Integer, nullable=False, server_default='1')
    timestamp = db.Column(db.Integer, nullable=False)
    whitelistset = db.Column(db.String(1024), nullable=False)

    def __init__(self, wid='0', mz='', active=0, negative=0, whitelistset='', timestamp=0):
        self.wid = wid
        self.mz = mz
        self.active = active
        self.negative = negative
        self.whitelistset = whitelistset
        self.timestamp = timestamp
        self.warnings = []
        self.error = []

    def __str__(self):
        return 'BasicRule {} wl:{} "mz:{}";'.format('negative' if self.negative else '', self.wid, self.mz)

    def __validate_wid(self, wid):
        if not re.match(r'wl:(\-?\d+,)*\-?\d+', wid):
            self.error.append('Illegal character in the whitelist id.')
            return False
        self.wid = wid
        return True

    def __validate_mz(self, mz):
        # Borrow '__validate_matchzone' from naxsi_rules.py ?
        self.mz = mz
        return True

    def parse(self, str_wl):
        self.warnings = list()
        self.error = list()

        lexer = shlex(str_wl)
        lexer.whitespace_split = True
        split = list(iter(lexer.get_token, ''))

        for piece in split:
            if piece == ';':
                continue
            elif piece.startswith(('"', "'")) and (piece[0] == piece[-1]):  # remove (double-)quotes
                piece = piece[1:-1]

            if piece == 'BasicRule':
                continue
            elif piece.startswith('wl:'):
                self.__validate_wid(piece)
            elif piece.startswith('mz:'):
                self.__validate_mz(piece[3:])
            elif piece == 'negative':
                self.negative = True
            else:
                self.error.append('Unknown fragment: {}'.format(piece))
                return False

            if not piece.islower():
                self.warnings.append('Your whitelist is not completely in lowercase.')

        if 'BasicRule' not in split:
            self.error.append("No 'BasicRule' keyword in {}.".format(str_wl))
            return False

        return True

    def validate(self):
        self.warnings = list()
        self.error = list()

        self.__validate_wid(self.wid)
        self.__validate_mz(self.mz)
        return True

    def explain(self):
        def __linkify_rule(_rid):
            if NaxsiRules.query.filter(NaxsiRules.sid == self.wid).first() is None:
                return _rid
            return '<a href="{}">{}</a>'.format(url_for('rules.view', sid=_rid), self.wid)

        if self.wid == 'wl:0':
            ret = 'Whitelist all rules'
        elif self.wid[3:].isdigit():
            ret = 'Whitelist the rule {}'.format(__linkify_rule(self.wid[3:]))
        else:
            zones = list()
            for rid in self.wid[3:].split(','):
                if rid.startswith('-'):
                    zones.append('except the rule {}'.format(__linkify_rule(rid[1:])))
                else:
                    zones.append('the rule {}'.format(__linkify_rule(rid)))
            ret = 'Whitelist ' + ', '.join(zones)

        if not self.mz:
            return ret + '.'

        return ret + ' if matching in {}.'.format(self.mz)
