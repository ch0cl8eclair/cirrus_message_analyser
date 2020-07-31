from main.model.model_utils import get_transform_step_from_payload, translate_step_type_to_payload_type


class PayloadTransformMapper:
    HEADINGS = ["tracking-point", "type", "transform-step-name", "url", "transform-step-type"]

    def __init__(self, payloads, transforms):
        self.payloads = payloads
        self.transforms = transforms
        self.mapping_records = []

    def map(self):
        if not self.payloads:
            return
        for current_payload in self.payloads:
            transform_step = get_transform_step_from_payload(current_payload, self.transforms)
            self.mapping_records.append(self._create_record(current_payload, transform_step))

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
