from collections import Counter

import numpy as np
import torch

from .alignment import Alignment
from .datatype import NucleotideDataType
from ..core.model import Model
from ..core.utils import process_object


class SitePattern(Model):
    _tag = 'site_pattern'

    def __init__(self, id_, partials, weights):
        self.partials = partials
        self.weights = weights
        super(SitePattern, self).__init__(id_)

    def update(self, value):
        pass

    def handle_model_changed(self, model, obj, index):
        pass

    def handle_parameter_changed(self, variable, index, event):
        pass

    @classmethod
    def from_json(cls, data, dic):
        id_ = data['id']

        if isinstance(data['datatype'], str) and data['datatype'] == 'nucleotide':
            data_type = NucleotideDataType()
        else:
            data_type = process_object(data['datatype'], dic)

        alignment = process_object(data['alignment'], dic)
        partials, weights = compress_alignment(alignment, data_type)

        return cls(id_, partials, weights)


def get_dna_leaves_partials_compressed(alignment):
    weights = []
    keep = [True] * alignment.sequence_size

    patterns = {}
    indexes = {}
    for i in range(alignment.sequence_size):
        pat = tuple(alignment[name][i] for name in alignment)

        if pat in patterns:
            keep[i] = False
            patterns[pat] += 1.0
        else:
            patterns[pat] = 1.0
            indexes[i] = pat
    for i in range(alignment.sequence_size):
        if keep[i]:
            weights.append(patterns[indexes[i]])

    partials = []
    dna_map = {'a': [1.0, 0.0, 0.0, 0.0],
               'c': [0.0, 1.0, 0.0, 0.0],
               'g': [0.0, 0.0, 1.0, 0.0],
               't': [0.0, 0.0, 0.0, 1.0]}

    for name in alignment:
        temp = []
        for i, c in enumerate(alignment[name].symbols_as_string()):
            if keep[i]:
                temp.append(dna_map.get(c.lower(), [1., 1., 1., 1.]))
        tip_partials = torch.tensor(np.transpose(np.array(temp)), requires_grad=False)

        partials.append(tip_partials)

    for i in range(len(alignment) - 1):
        partials.append([None] * len(patterns.keys()))
    return partials, torch.tensor(np.array(weights))


def compress_alignment(alignment, data_type):
    """Compress alignment using data_type

    Parameters
    ----------
    alignment : Alignment
    data_type : DataType

    Returns
    -------
    tuple
        a tuple containing partials and weights
    """
    taxa, sequences = zip(*alignment)
    count_dict = Counter(list(zip(*sequences)))
    pattern_ordering = sorted(list(count_dict.keys()))
    patterns_list = list(zip(*pattern_ordering))
    weights = [count_dict[pattern] for pattern in pattern_ordering]
    patterns = dict(zip(taxa, patterns_list))

    partials = []

    for taxon in taxa:
        partials.append(torch.tensor(np.transpose(np.array([data_type.partial(c) for c in patterns[taxon]]))))

    for i in range(len(alignment) - 1):
        partials.append([None] * len(patterns.keys()))
    return partials, torch.tensor(np.array(weights))
