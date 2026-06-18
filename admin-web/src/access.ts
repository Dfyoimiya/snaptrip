export default function access(initialState: { currentUser?: API.CurrentUser }) {
  return {
    canAdmin: true,
    canRead: true,
  };
}
