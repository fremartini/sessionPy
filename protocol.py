class Protocol():
    def __init__(self, protoc : str) -> None:
        self.protoc = protoc

    def __str__(self) -> str:
        return self.protoc

    def projectStr(self, p : str) -> None:
        self._write(p)

    def projectFile(self, file : str) -> None:
        f = open(file, "r") 
        src = f.read()
        f.close()

        self._write(src)

    def _getLocalProjections(self, protocol : str):
        roles = dict()
        channels = dict()
        portNum = 5000

        for line in protocol.split(";"):
            if (line.strip() == ""): continue

            rolePair, typ = [_.strip() for _ in line.split(':')]
            a, b = [x.strip() for x in rolePair.split("->")]

            k = f"{a}{b}"
            if not k in channels:
                channels[k] = portNum
                channels[f"{b}{a}"] = portNum
                portNum = portNum + 1

            if not a in roles:
                roles[a] = []
            roles[a].append(("send(FILL_THIS_OUT)", b, typ))
            
            if not b in roles:
                roles[b] = []
            roles[b].append(("recv()", a, typ))

        return (roles, channels)

    def _write(self, protocol: str) -> None:
        fileHeader = "# THIS FILE IS AUTOGENERATED\nfrom channel import Channel\nfrom typeChecking import check_channels\n\n"

        roles, channels = self._getLocalProjections(protocol)

        print(roles, channels)

        for role, instructions in roles.items():
            with open(f"role_{role}.py", "w+", encoding='utf-8') as f:
                f.write(fileHeader)

                f.write("@check_channels\ndef run():\n")

                for instruction, peer, typ in instructions:
                    chName = f"{role}{peer}"
                    if (instruction == "recv()"):
                        chName = f"{peer}{role}"

                    ch = channels[chName]
                    f.write(f"\tch_{chName} = Channel({typ}, {ch})\n")

                f.write("\n")

                for instruction, peer, typ in instructions:
                    chName = f"{role}{peer}"
                    if (instruction == "recv()"):
                        chName = f"{peer}{role}"

                    f.write(f"\tch_{chName}.{instruction}\n")

                f.write("run()")