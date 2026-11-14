import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import pageSchema from '../../../../contracts/schemas/entertainment/feed-page.v1.schema.json';
import userSchema from '../../../../contracts/schemas/identity/current-user.v1.schema.json';
import type { CurrentUser, EntertainmentFeedPage, PlaybackSource } from './generated';

const ajv = new Ajv({ allErrors: true, strict: false });
addFormats(ajv);
const page = ajv.compile<EntertainmentFeedPage>(pageSchema);
const user = ajv.compile<CurrentUser>(userSchema);
const playback = ajv.compile<PlaybackSource>({ ...pageSchema.definitions.PlaybackSource });
export function parseFeedPage(value: unknown): EntertainmentFeedPage {
  if (!page(value)) throw new Error('The feed response does not match entertainment contract v1.');
  return value;
}
export function parseCurrentUser(value: unknown): CurrentUser {
  if (!user(value)) throw new Error('The user does not match identity contract v1.');
  return value;
}
export function parsePlayback(value: unknown): PlaybackSource {
  if (!playback(value)) throw new Error('The playback response does not match entertainment contract v1.');
  return value;
}
