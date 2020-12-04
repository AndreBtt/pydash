# -*- coding: utf-8 -*-
"""
@author: Éden Medeiros

@description: Trabalho de Transmissão de Dados
"""
import math
import time

from player.parser import *
from r2a.ir2a import IR2A


class R2AEden(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)

        self.parsed_mpd = ''
        self.qi = []
        self.request_qi = 0

        self.request_time = 0
        self.last_index = 0
        self.throughput = []  # São guardados no máximo 3 amostras
        self.times_paused = 0
        self.paused_last_time = False

        # Controla a qualidade do segmento baixado.
        # Varia de 0 a 1. Quanto mais perto do 1, melhor será a qualidade baixada.
        self.factor = 0

    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter()
        self.send_down(msg)

    def handle_xml_response(self, msg):
        self.request_time = time.perf_counter() - self.request_time
        self.throughput.insert(self.last_index, msg.get_bit_length() / self.request_time)
        self.last_index = (self.last_index + 1) % 3

        self.parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = self.parsed_mpd.get_qi()

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        self.request_time = time.perf_counter()

        self.request_qi = math.floor((len(self.qi) - 1) * self.factor)

        msg.add_quality_id(self.qi[self.request_qi])
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        self.request_time = time.perf_counter() - self.request_time
        throughput = msg.get_bit_length() / self.request_time

        self.throughput.insert(self.last_index, throughput)
        self.last_index = (self.last_index + 1) % 3

        # Throughput afeta 20% no fator.
        if throughput > self.qi[self.request_qi]:
            self.increase_factor_by(0.2)
        else:
            self.decrease_factor_by(0.2)

        # A quantidade de videos pra tocar, afeta 60% positivamente e 30% negativamente.
        if self.whiteboard.get_amount_video_to_play() > 5:
            self.increase_factor_by(0.6)
        else:
            self.decrease_factor_by(0.3)

        if len(self.whiteboard.get_playback_pauses()) > self.times_paused:
            self.times_paused = len(self.whiteboard.get_playback_pauses())
            self.paused_last_time = True
        else:
            self.paused_last_time = False

        # O video ter sido pausado, afeta drasticamente o fator.
        # 80% negativamente e 10% positivamente se não ocorreu nenhuma pausa desde a última requisição.
        if self.paused_last_time:
            self.decrease_factor_by(0.8)
        else:
            self.increase_factor_by(0.1)

        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass

    def increase_factor_by(self, value):
        self.factor = min(1, self.factor + value)

    def decrease_factor_by(self, value):
        self.factor = max(0, self.factor - value)
