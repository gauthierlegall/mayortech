export const MAX_STATE_BYTES = 2_000_000;

export function encodeState(bytes, maximum = MAX_STATE_BYTES) {
  if (!(bytes instanceof Uint8Array)) throw new Error('invalid_state');
  if (bytes.length > maximum) throw new Error('state_too_large');
  let binary = '';
  for (let index = 0; index < bytes.length; index += 16_384) {
    binary += String.fromCharCode(...bytes.subarray(index, index + 16_384));
  }
  return btoa(binary);
}

export function decodeState(encoded, maximum = MAX_STATE_BYTES) {
  if (typeof encoded !== 'string' || encoded.length > Math.ceil(maximum / 3) * 4
      || encoded.length % 4 !== 0
      || !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(encoded)) {
    throw new Error('invalid_state');
  }
  const bytes = Uint8Array.from(atob(encoded), char => char.charCodeAt(0));
  if (bytes.length > maximum) throw new Error('state_too_large');
  if (encodeState(bytes, maximum) !== encoded) throw new Error('invalid_state');
  return bytes;
}

export function normalizeStateResponse(response) {
  if (!response || typeof response !== 'object'
      || !Object.hasOwn(response, 'state_base64')
      || !Object.hasOwn(response, 'revision_hash')
      || (response.revision_hash !== null && (typeof response.revision_hash !== 'string'
          || !/^[a-f0-9]{64}$/.test(response.revision_hash)))
      || (response.state_base64 !== null && typeof response.state_base64 !== 'string')) {
    throw new Error('invalid_state_response');
  }
  return {...response, state: decodeState(response.state_base64 ?? '')};
}
