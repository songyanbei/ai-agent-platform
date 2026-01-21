"""
文档管理模块
负责文档去重和全局引用索引管理
"""
import hashlib
from typing import List, Dict, Any, Optional
from shared.utils.logger import setup_logger

logger = setup_logger("document_manager")


class Document:
    """文档数据类"""
    
    def __init__(
        self,
        content: str,
        source: str,
        knowledge_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.content = content
        self.source = source
        self.knowledge_id = knowledge_id
        self.metadata = metadata or {}
        self.index: Optional[int] = None  # 全局引用索引
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.index,
            "content": self.content,
            "source": self.source,
            "knowledge_id": self.knowledge_id,
            **self.metadata
        }


class DocumentManager:
    """
    文档管理器
    
    功能：
    1. 文档去重（基于内容哈希）
    2. 维护全局引用索引（从 1 开始）
    3. 生成参考文献列表
    """
    
    def __init__(self):
        self.documents: List[Document] = []  # 存储唯一文档
        self.doc_hash_map: Dict[str, int] = {}  # 哈希 -> 索引映射
        
    def _compute_hash(self, doc: Document) -> str:
        """
        计算文档哈希值
        
        使用切片ID（chunk_id）或内容哈希来去重
        注意：不使用文档ID（doc_id），因为同一文档的不同切片需要保留
        
        Args:
            doc: 文档对象
            
        Returns:
            str: MD5 哈希值
        """
        # 优先使用 knowledge_id（切片ID），如果没有则使用内容哈希
        if doc.knowledge_id:
            hash_source = doc.knowledge_id
        else:
            hash_source = doc.content
        
        return hashlib.md5(hash_source.encode('utf-8')).hexdigest()
    
    def add_document(self, doc: Document) -> int:
        """
        添加文档（自动去重）
        
        Args:
            doc: 文档对象
            
        Returns:
            int: 该文档的全局索引（1-based）
        """
        doc_hash = self._compute_hash(doc)
        
        # 如果已存在，返回已有索引
        if doc_hash in self.doc_hash_map:
            return self.doc_hash_map[doc_hash]
        
        # 添加新文档
        index = len(self.documents) + 1
        doc.index = index
        self.documents.append(doc)
        self.doc_hash_map[doc_hash] = index
        
        return index
    
    def add_documents(self, docs: List[Document]) -> List[int]:
        """
        批量添加文档
        
        Args:
            docs: 文档列表
            
        Returns:
            List[int]: 每个文档的全局索引列表
        """
        return [self.add_document(doc) for doc in docs]
    
    def get_document(self, index: int) -> Optional[Document]:
        """
        根据索引获取文档
        
        Args:
            index: 文档索引（1-based）
            
        Returns:
            Optional[Document]: 文档对象，如果不存在返回 None
        """
        if 1 <= index <= len(self.documents):
            return self.documents[index - 1]
        return None
    
    def get_all_documents(self) -> List[Document]:
        """获取所有文档"""
        return self.documents.copy()
    
    def sort_documents(self, key: str = "score", reverse: bool = True):
        """
        对文档进行排序并重新分配引用序号
        
        Args:
            key: 排序依据的metadata字段，默认为 "score"（相似度分数）
            reverse: 是否降序排序，默认 True（分数高的在前）
        
        注意：
        - 排序后会重新分配 index（1, 2, 3...）
        - 原始的 chunk_id 保留在 knowledge_id 中
        """
        try:
            # 按指定字段排序
            self.documents.sort(
                key=lambda doc: doc.metadata.get(key, 0) if doc.metadata else 0,
                reverse=reverse
            )
            
            # 重新分配序号
            for idx, doc in enumerate(self.documents, start=1):
                doc.index = idx
            
            logger.info(f"文档已按 {key} {'降序' if reverse else '升序'} 排序，重新分配序号")
        
        except Exception as e:
            logger.error(f"文档排序失败: {e}", exc_info=True)
    
    def get_context_for_llm(self, max_docs: int = None) -> str:
        """
        生成用于 LLM 的上下文字符串
        
        Args:
            max_docs: 最多使用的文档数量,None表示使用全部
        
        Returns:
            str: 格式化的文档上下文
        """
        if not self.documents:
            return ""
        
        # 限制文档数量
        docs_to_use = self.documents[:max_docs] if max_docs else self.documents
        
        context_parts = []
        for doc in docs_to_use:
            # 格式：[序号] 来源：xxx\n内容：xxx
            # 注意：这里的序号是排序后的 index，用于引用
            part = f"[{doc.index}] 来源：{doc.source}\n内容：{doc.content}"
            context_parts.append(part)
        
        return "\n\n".join(context_parts)
    
    def get_references(self, max_docs: int = None) -> List[Dict[str, Any]]:
        """
        生成参考文献列表(用于 message_type: 204)
        
        返回按文档分组并排序的文章列表,而不是所有切片
        - 按 doc_id 分组(同一文章的多个切片合并为一条)
        - 按最高分数排序
        - 如果没有 doc_id,则按切片处理
        
        Args:
            max_docs: 最多返回的文档数量,None表示返回全部
        
        Returns:
            List[Dict]: 参考文献列表
        """
        # 限制文档数量
        docs_to_process = self.documents[:max_docs] if max_docs else self.documents
        
        # 按 doc_id 分组
        doc_groups = {}  # doc_id -> {max_score, source, doc_url, chunks}
        no_doc_id_items = []  # 没有 doc_id 的切片
        
        for doc in docs_to_process:
            doc_id = doc.metadata.get("doc_id") if doc.metadata else None
            
            if doc_id:
                # 有 doc_id,按文档分组
                if doc_id not in doc_groups:
                    doc_groups[doc_id] = {
                        "doc_id": doc_id,
                        "source": doc.source,
                        "max_score": doc.metadata.get("score", 0) if doc.metadata else 0,
                        "doc_url": doc.metadata.get("doc_url") if doc.metadata else None,
                        "knowledge_base_id": doc.metadata.get("knowledge_base_id") if doc.metadata else None,
                        "knowledge_base_name": doc.metadata.get("knowledge_base_name") if doc.metadata else None,
                        "chunks": []
                    }
                
                # 更新最高分数
                current_score = doc.metadata.get("score", 0) if doc.metadata else 0
                if current_score > doc_groups[doc_id]["max_score"]:
                    doc_groups[doc_id]["max_score"] = current_score
                
                # 添加切片信息
                doc_groups[doc_id]["chunks"].append({
                    "chunk_id": doc.knowledge_id,
                    "score": current_score,
                    "content_preview": doc.content[:100] + "..." if len(doc.content) > 100 else doc.content
                })
            else:
                # 没有 doc_id,单独处理
                no_doc_id_items.append({
                    "chunk_id": doc.knowledge_id,
                    "source": doc.source,
                    "score": doc.metadata.get("score", 0) if doc.metadata else 0,
                    "content_preview": doc.content[:100] + "..." if len(doc.content) > 100 else doc.content,
                    "knowledge_base_id": doc.metadata.get("knowledge_base_id") if doc.metadata else None,
                    "knowledge_base_name": doc.metadata.get("knowledge_base_name") if doc.metadata else None
                })
        
        # 将分组的文档转换为列表并按分数排序
        references = list(doc_groups.values())
        references.sort(key=lambda x: x["max_score"], reverse=True)
        
        # 添加没有 doc_id 的切片(也按分数排序)
        no_doc_id_items.sort(key=lambda x: x["score"], reverse=True)
        
        # 合并结果并分配序号
        all_references = []
        for idx, ref in enumerate(references, start=1):
            ref["id"] = idx
            ref["title"] = ref["source"]  # 使用 source 作为标题
            ref["chunk_count"] = len(ref["chunks"])  # 该文章的切片数量
            all_references.append(ref)
        
        # 添加没有 doc_id 的项
        for idx, ref in enumerate(no_doc_id_items, start=len(all_references) + 1):
            ref["id"] = idx
            ref["title"] = ref["source"]
            all_references.append(ref)
        
        used_docs = len(docs_to_process)
        total_docs = len(self.documents)
        logger.info(f"生成参考文献: {len(all_references)} 篇文章 (使用 {used_docs}/{total_docs} 个切片)")
        
        return all_references
    
    def clear(self):
        """清空所有文档"""
        self.documents.clear()
        self.doc_hash_map.clear()
    
    def __len__(self) -> int:
        """返回文档数量"""
        return len(self.documents)
    
    def __repr__(self) -> str:
        return f"<DocumentManager: {len(self.documents)} documents>"
