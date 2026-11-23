from medium88_polished import MediumScene as CableScene
from medium88_room_details import MediumScene as DeviceScene

class R31Scene(CableScene):

    def controls_for(self, i, s, root):
        super().controls_for(i, s, root)
        if s.get('visual', {}).get('type') == 'heights':
            for node in self.buffers[i]:
                self.visibility(node, False)
            self.box('height_input_mount', [0, 0.26, 1.47], [0.95, 0.05, 0.2], 'wood', root)
            self.box('height_input_bezel', [0, 0.22, 1.47], [0.9, 0.035, 0.16], 'iron', root)

    def screen(self, key, parent, pos, w, h, im, sig):
        if key == 's1_buffer':
            pos = [0, 0.198, 1.47]
        return super().screen(key, parent, pos, w, h, im, sig)

class R27Scene(DeviceScene):

    def float_key(self, i, s, root):
        super().float_key(i, s, root)
        self.cylinder('faucet_valve_stem', [0.36, 0.135, 1.2525], 0.009, 0.065, 'steel', 'z', root)
