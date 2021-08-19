from collections import Counter
from typing import List, Optional, Tuple, Union

import torch

from ..core.model import Model
from ..core.utils import process_object
from .alignment import Alignment
from .datatype import DataType, NucleotideDataType


class SitePattern(Model):
    _tag = 'site_pattern'

    def __init__(
        self, id_: Optional[str], partials: List[torch.Tensor], weights: torch.Tensor
    ) -> None:
        super().__init__(id_)
        self.partials = partials
        self.weights = weights

    def update(self, value):
        pass

    def handle_model_changed(self, model, obj, index):
        pass

    def handle_parameter_changed(self, variable, index, event):
        pass

    def cuda(self, device: Optional[Union[int, torch.device]] = None) -> None:
        self.weights = self.weights.cuda(device)
        for idx, partial in enumerate(self.partials):
            if partial is None:
                break
            self.partials[idx] = partial.cuda(device)

    def cpu(self) -> None:
        self.weights = self.weights.cpu()
        for idx, partial in enumerate(self.partials):
            if partial is None:
                break
            self.partials[idx] = partial.cpu()

    @property
    def sample_shape(self) -> torch.Size:
        raise RuntimeError('Do not call sample_shape on a SitePattern')

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


def compress_alignment(
    alignment: Alignment, data_type: DataType
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Compress alignment using data_type.

    :param Alignment alignment: sequence alignment
    :param DataType data_type: data type
    :return: a tuple containing partials and weights
    :rtype: Tuple[torch.Tensor, torch.Tensor]
    """
    taxa, sequences = zip(*alignment)
    count_dict = Counter(list(zip(*sequences)))
    pattern_ordering = sorted(list(count_dict.keys()))
    patterns_list = list(zip(*pattern_ordering))
    weights = torch.tensor(
        [count_dict[pattern] for pattern in pattern_ordering], dtype=torch.float64
    )
    patterns = dict(zip(taxa, patterns_list))

    partials = []

    for taxon in taxa:
        partials.append(
            torch.tensor(
                [data_type.partial(c) for c in patterns[taxon]], dtype=torch.float64
            ).t()
        )

    for i in range(len(alignment) - 1):
        partials.append([None] * len(patterns.keys()))
    return partials, weights
