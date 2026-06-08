/** OSS 签名结果 */
export interface OssPolicyResult {
  accessKeyId: string
  policy: string
  signature: string
  dir: string
  host: string
  expire: number
}
