export default function Badge({ tone = "gray", children }) {
  return <span className={"badge " + tone}>{children}</span>;
}