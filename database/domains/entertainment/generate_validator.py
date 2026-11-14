"""Regenerate only the embedded v1 wire validator; Mongo lifecycle fields stay owned here."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def compile_wire(value, definitions):
    if isinstance(value, list):
        return [compile_wire(item, definitions) for item in value]
    if not isinstance(value, dict):
        return value
    if '$ref' in value:
        return compile_wire(definitions[value['$ref'].rsplit('/', 1)[-1]], definitions)
    result = {}
    for key, item in value.items():
        if key in ('$schema', 'title', 'format', 'definitions'):
            continue  # formats (zoned times, URLs) are additionally enforced by normalization
        if key == 'const':
            result['enum'] = [item]
        elif key == 'type':
            convert = lambda kind: 'int' if kind == 'integer' else kind
            result['bsonType'] = [convert(kind) for kind in item] if isinstance(item, list) else convert(item)
        else:
            result[key] = compile_wire(item, definitions)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    wire = json.loads((ROOT / 'contracts/schemas/entertainment/feed-page.v1.schema.json').read_text())
    path = Path(__file__).with_name('manifest.json')
    manifest = json.loads(path.read_text())
    field = manifest['collections'][0]['validator']['$jsonSchema']['properties']['items']
    generated = compile_wire(wire['definitions']['EntertainmentVideo'], wire['definitions'])
    if args.check:
        if generated != field['items']:
            raise SystemExit('Owned Mongo validator drifted from the v1 wire schema. Regenerate it.')
        print('Owned Mongo validator matches the v1 wire schema.')
    else:
        field['items'] = generated
        path.write_text(json.dumps(manifest, indent=2) + '\n')
