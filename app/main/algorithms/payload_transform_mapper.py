from main.config.constants import VALIDATE, TRANSFORM
from main.model.model_utils import get_transform_step_from_payload, translate_step_type_to_payload_type, \
    SuspectedMissingTransformsException, get_matching_transform_step, \
    obtain_transform_details_from_payload_tracking_point


class PayloadTransformMapper:
    HEADINGS = ["tracking-point", "type", "transform-step-name", "url", "transform-step-type"]

    def __init__(self, payloads, transforms):
        self.payloads = payloads
        self.transforms = transforms
        self.mapping_records = []

    def reset(self, transforms):
        self.transforms = transforms
        self.mapping_records = []

    def map(self):
        if not self.payloads:
            return
        missing_transforms = 0
        for current_payload in self.payloads:
            transform_details_tuple = obtain_transform_details_from_payload_tracking_point(current_payload)
            if transform_details_tuple:
                stage_type, transform_name, transform_step_name = transform_details_tuple
                transform_step = get_matching_transform_step(self.transforms, stage_type, transform_name, transform_step_name)
                if not transform_step and stage_type in [TRANSFORM, VALIDATE]:
                    missing_transforms = missing_transforms + 1
            else:
                transform_step = None
            self.mapping_records.append(self._create_record(current_payload, transform_step))
        if missing_transforms:
            raise SuspectedMissingTransformsException()

    def get_records(self):
        return self.mapping_records

    def _create_record(self, current_payload, transform_step):
        new_record = {'tracking-point': current_payload.get("tracking-point")}
        if transform_step:
            new_record['type'] = translate_step_type_to_payload_type(transform_step.get("transform-step-type"))
            new_record['transform-step-name'] = transform_step.get("transform-step-name")
            new_record['url'] = transform_step.get("url")
            new_record['transform-step-type'] = transform_step.get("transform-step-type")
        return new_record
