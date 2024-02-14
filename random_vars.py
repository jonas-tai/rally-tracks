from scipy.stats import pareto, zipfian, expon, uniform, multinomial, rv_continuous, norm
import numpy as np


class RandomVar:
    def __init__(self, rv: rv_continuous) -> None:
        self.rv = rv
        self.draws = []

    def draw(self):
        x = self.rv.rvs()
        self.add_to_history(x)
        return x

    def add_to_history(self, x):
        self.draws.append(x)


class LoadLevel(RandomVar):
    def __init__(self, period, clients, step_size, jitter=0, mean_load=0.5, clip=(0, 1), static_load_level=True) -> None:
        super().__init__(norm(scale=jitter))
        self.clip = clip
        self.jitter = jitter
        self.period = period
        self.clients = clients
        self.mean_load = mean_load
        self.step_size = step_size
        self.static_load_level = True

    def draw(self):
        if self.static_load_level:
            return self.clients
        if self.jitter > 0:
            noise = self.rv.rvs()
        else:
            noise = 0

        iteration = len(self.draws) * self.step_size
        # clip it so we don't have too much load or too little (or negative)
        scale = np.clip(
            (1-self.mean_load) * np.sin(iteration * 2 * np.pi / self.period) + self.mean_load + noise,
            self.clip[0],
            self.clip[1]
        )
        out = int(np.ceil(self.clients * scale))
        self.add_to_history(out)
        return out


class ExponRV(RandomVar):
    def __init__(self, a) -> None:
        rv = expon(scale=a)
        super().__init__(rv)


class ZipfianRV(RandomVar):
    def __init__(self, a, n) -> None:
        # loc=-1 to 0 index it
        rv = zipfian(a=a, n=n, loc=-1)
        super().__init__(rv)
        self.n = n
    
    def pmf(self):
        return self.rv.pmf(np.arange(self.n))

class MultiNominalRV(RandomVar):
    def __init__(self, probs) -> None:
        rv = multinomial(1, probs)
        super().__init__(rv)
        
    def draw(self):
        drawn_values = self.rv.rvs()
        x = np.argmax(drawn_values)
        super().add_to_history(x)
        return x

class RequestSize(RandomVar):
    def __init__(self, b, loc, clip=(0, None)) -> None:
        pareto_rv = pareto(b, loc=loc, scale=1)
        self.probs = None
        self.categories = None
        if clip[1] is not None:
            self.categories = np.arange(loc + 1, clip[1])
            # add 1 since we diff later
            cdfs = pareto_rv.cdf(np.arange(loc + 1, clip[1] + 1))
            diffs = np.diff(cdfs)
            self.probs = diffs / diffs.sum()
            rv = None
        else:
            rv = pareto_rv
        super().__init__(rv)
        self.clip = clip

    def draw(self):
        if self.probs is not None:
            if len(self.probs) > 0:
                idx = np.random.choice(self.categories, p=self.probs)
                self.add_to_history(idx)
                return idx
            else:
                return 0
        else:
            return super().draw()
        # x = self.rv.rvs()
        # idx = np.where(x[0] == 1)
        # out = int(idx[0])
        # self.add_to_history(out)
        # return out
