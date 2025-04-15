import click
import libasvat.command_utils as cmd_utils


@cmd_utils.main_command_group
class FactorioCommands(metaclass=cmd_utils.Singleton):
    """FACTORIO RELATED COMMANDS"""

    def __init__(self):
        pass

    @cmd_utils.object_identifier
    def name(self):
        return "factorio"

    @cmd_utils.sub_group_getter(options=["nulius", "ultracube"])
    def subgroup(self, name):
        """Gets the given subgroup"""
        if name == "nulius":
            return NuliusCommands()
        elif name == "ultracube":
            return UltracubeCommands()


class NuliusCommands(metaclass=cmd_utils.Singleton):
    """Nulius mod-pack related commands"""

    def __init__(self):
        pass

    def _solar_watts(self, n, mark=1):
        solars = [
            150,
            300,
            600,
        ]
        base_solar_power = solars[mark-1]
        bonus = 0.1
        solar2 = base_solar_power*(1 + 2*bonus)
        solar3 = base_solar_power*(1 + 3*bonus)
        solar4 = base_solar_power*(1 + 4*bonus)
        total = n**2
        total -= 4
        W = 4*solar2
        if total == 0:
            return W
        total -= (n-2)*4
        W += (n-2)*4*solar3
        W += total*solar4
        return W / 1000  # return in MW

    @cmd_utils.instance_command()
    @click.option("--solar-mark", "-s", type=int, default=3)
    @click.option("--exchanger-mark", "-e", type=int, default=2)
    @click.argument("num", type=int)
    def solar_energy(self, num, solar_mark, exchanger_mark):
        """Calculates amount of solar energy that a square of NUMxNUM thermal solar panels generate in
        Nulius mod"""
        w = self._solar_watts(num, mark=solar_mark)
        exchangers = [
            1.8,  # in MW
            8.5,
            20,
        ]
        exchanger_rate = exchangers[exchanger_mark-1]
        e = w / exchanger_rate
        click.secho(f"{num}x{num} solar-panels-mk{solar_mark} generate {w} MW with {e:.1f} exchangers-mk{exchanger_mark}", fg="green")

    @cmd_utils.instance_command()
    @click.option("--stirling", "-s", is_flag=True)
    @click.argument("num", type=int)
    def nuclear_energy(self, num, stirling=False):
        """Calculates amount of energy that a row of 2xNUM reactors generate in Nulius mod"""
        base_reactor_power = 50  # MW
        total = 2*num
        bonus = 0.5
        if total < 4:
            w = total * base_reactor_power * (1+bonus)
        else:
            total -= 4
            w = 4 * base_reactor_power * (1 + 2*bonus)
            w += total * base_reactor_power * (1 + 3*bonus)
        if stirling:
            generator_rate = 8
            generator_name = "stirling-engine-mk3"
        else:
            generator_rate = 20  # MW
            generator_name = "exchanger-mk3"
        e = w / generator_rate
        click.secho(f"2x{num} reactors generate {w} MW with {e:.1f} {generator_name}", fg="green")


class UltracubeCommands(metaclass=cmd_utils.Singleton):
    """UltraCube mod-pack related commands"""

    def _reactors(self, n):
        """N = num reactors
        returns energia em MW
        """
        e = 80
        b = 0.25
        total = 0
        while n > 4:
            n -= 2
            total += 2 * (e * (1+3*b))
        total += n * (e * (1 + 2*b))
        return total

    @cmd_utils.instance_command()
    @click.argument("num", type=int)
    def nuclear(self, num):
        r = self._reactors(num)
        exc = r / 10
        tur = exc * 103 / 60
        print(f"Reactors = {r}")
        print(f"Exchangers = {exc}")
        print(f"Turbines = {tur}")
        print(f"Offshore Pumps = {exc*103/1200}")
        print(f"\nIsso gera {tur * 6} MW")
