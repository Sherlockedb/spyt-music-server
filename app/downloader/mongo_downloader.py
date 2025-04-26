import logging
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.downloader.base_downloader import BaseSpotifyDownloader
from app.core.config import settings

class MongoDBSpotifyDownloader(BaseSpotifyDownloader):
    """
    MongoDB Spotify 下载器 - 同步版本
    """
    
    def __init__(self, mongodb_url=None, db_name=None, client_id=None, client_secret=None, 
                 output_root=None, output_format=None, use_artist_dir=True, 
                 max_retries=None, retry_delay=None, log_file=None,
                 collection_prefix=""):
        """初始化下载器"""
        # 使用配置中的默认值
        client_id = client_id or settings.SPOTIFY_CLIENT_ID
        client_secret = client_secret or settings.SPOTIFY_CLIENT_SECRET
        output_root = output_root or settings.MUSIC_LIBRARY_PATH
        mongodb_url = mongodb_url or settings.MONGODB_URL
        db_name = db_name or settings.MONGODB_DB
        
        # 如果没有指定输出格式，使用默认格式
        if output_format is None:
            output_format = "{album}/[{artists}] {track-number}-{title}.{output-ext}"
        
        # 如果没有指定重试参数，使用默认值
        max_retries = max_retries if max_retries is not None else 3
        retry_delay = retry_delay if retry_delay is not None else 5
        
        # 如果没有指定日志文件，使用配置中的值
        log_file = log_file or settings.LOG_FILE
        
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            output_root=output_root,
            output_format=output_format,
            use_artist_dir=use_artist_dir,
            max_retries=max_retries,
            retry_delay=retry_delay,
            log_file=log_file
        )
        
        # 初始化MongoDB连接
        self.client = MongoClient(mongodb_url)
        self.db = self.client[db_name]
        self.collection_prefix = collection_prefix
    
    def _get_collection_name(self, entity_type, suffix):
        """获取集合名称"""
        return f"{self.collection_prefix}{entity_type}_{suffix}"
    
    def _save_stats(self, entity_type, entity_id, stats):
        """将统计信息保存到 MongoDB"""
        try:
            collection_name = self._get_collection_name(entity_type, "stats")
            collection = self.db[collection_name]
            
            # 将 entity_id 作为 _id 字段
            stats_copy = stats.copy()
            stats_copy['_id'] = entity_id
            
            # 使用 upsert=True 来插入或更新
            collection.replace_one({'_id': entity_id}, stats_copy, upsert=True)
            
            logging.info(f"统计信息已保存到 MongoDB: {entity_type}_{entity_id}")
            return True
        except PyMongoError as e:
            logging.error(f"保存统计信息到 MongoDB 失败: {e}")
            return False
    
    def _save_info(self, entity_type, entity_id, info):
        """将元数据信息保存到 MongoDB"""
        try:
            collection_name = self._get_collection_name(entity_type, "info")
            collection = self.db[collection_name]
            
            # 创建一个新的文档，包含 _id 和元数据
            document = {
                '_id': entity_id,
                'info': info
            }
            
            # 使用 upsert=True 来插入或更新
            collection.replace_one({'_id': entity_id}, document, upsert=True)
            
            logging.info(f"元数据信息已保存到 MongoDB: {entity_type}_{entity_id}")
            return True
        except PyMongoError as e:
            logging.error(f"保存元数据信息到 MongoDB 失败: {e}")
            return False
    
    def _load_stats(self, entity_type, entity_id):
        """从 MongoDB 加载统计信息"""
        try:
            collection_name = self._get_collection_name(entity_type, "stats")
            collection = self.db[collection_name]
            
            document = collection.find_one({'_id': entity_id})
            
            if document:
                logging.info(f"从 MongoDB 加载了统计信息: {entity_type}_{entity_id}")
                # 删除 _id 字段，使结果与基类期望的格式一致
                if '_id' in document:
                    document_copy = document.copy()
                    del document_copy['_id']
                    return document_copy
                return document
            else:
                logging.info(f"MongoDB 中没有找到统计信息: {entity_type}_{entity_id}")
                return None
                
        except PyMongoError as e:
            logging.warning(f"从 MongoDB 加载统计信息失败: {e}")
            return None
    
    def _load_info(self, entity_type, entity_id):
        """从 MongoDB 加载元数据信息"""
        try:
            collection_name = self._get_collection_name(entity_type, "info")
            collection = self.db[collection_name]
            
            document = collection.find_one({'_id': entity_id})
            
            if document and 'info' in document:
                logging.info(f"从 MongoDB 加载了元数据信息: {entity_type}_{entity_id}")
                return document['info']
            else:
                logging.info(f"MongoDB 中没有找到元数据信息: {entity_type}_{entity_id}")
                return None
                
        except PyMongoError as e:
            logging.warning(f"从 MongoDB 加载元数据信息失败: {e}")
            return None
    
    def close(self):
        """关闭MongoDB连接"""
        if hasattr(self, 'client'):
            self.client.close()
            logging.info("已关闭MongoDB连接")