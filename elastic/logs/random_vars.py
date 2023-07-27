from scipy.stats import pareto, zipfian, expon, uniform, multinomial, rv_continuous
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
    def __init__(self, period, clients, jitter=0, clip=(0, 1)) -> None:
        super().__init__(uniform(loc=-jitter, scale=2 * jitter))
        self.clip = clip
        self.jitter = jitter
        self.period = period
        self.clients = clients

    def draw(self):
        if self.jitter > 0:
            noise = self.rv.rvs()
        else:
            noise = 0

        iteration = len(self.draws)
        # clip it so we don't have too much load or too little (or negative)
        scale = np.clip(
            np.sin(iteration * 2 * np.pi / self.period) + noise,
            self.clip[0],
            self.clip[1]
        )
        out = int(np.round(self.clients * scale))
        self.add_to_history(out)
        return out


class ExponRV(RandomVar):
    def __init__(self, lda) -> None:
        rv = expon(1 / lda)
        super().__init__(rv)


class RequestType(RandomVar):
    def __init__(self, a, n) -> None:
        # loc=-1 to 0 index it
        rv = zipfian(a, n, loc=-1)
        super().__init__(rv)


class RequestSize(RandomVar):
    def __init__(self, b, clip=(0, None)) -> None:
        pareto_rv = pareto(b, loc=-1, scale=1)
        self.probs = None
        self.categories = None
        if clip[1] is not None:
            self.categories = np.arange(clip[1])
            # add 1 since we diff later
            cdfs = pareto_rv.cdf(np.arange(clip[1] + 1))
            diffs = np.diff(cdfs)
            self.probs = diffs / diffs.sum()
            rv = None
        else:
            rv = pareto_rv
        super().__init__(rv)
        self.clip = clip

    def draw(self):
        if self.probs is not None:
            idx = np.random.choice(self.categories, p=self.probs)
            self.add_to_history(idx)
            return idx
        else:
            return super().draw()
        # x = self.rv.rvs()
        # idx = np.where(x[0] == 1)
        # out = int(idx[0])
        # self.add_to_history(out)
        # return out
