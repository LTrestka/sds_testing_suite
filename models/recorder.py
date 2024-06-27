import copy


class CommandRecorder:
    def __init__(self):
        self.parts = {}
        self.commands = []
    
    def add_command(self, command):
        self.command.append(command)
    
    def add_part(self, index, part):
        if index not in self.parts:
            self.parts[index] = [str(part)]
        else:
            self.parts[index].append(str(part))
    
    def finalize_part(self, index):
        if index in self.parts:
            self.commands.append(' '.join(str(self.parts[index])))
            del self.parts[index]
    
    def finalize(self):
        return list(copy.deepcopy(self.commands))
    
    def dump(self):
        del self

cmd = CommandRecorder()
cmd.add_command("echo 'hello")
