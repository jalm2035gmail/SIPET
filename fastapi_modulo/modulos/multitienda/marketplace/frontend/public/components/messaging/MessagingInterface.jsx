import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import {
  Send, Paperclip, Smile, Search, Filter, Clock, Check, CheckCheck,
  User, Store, Package, AlertCircle, Archive, Tag, MoreVertical,
  Download, Trash2, Pin, Star, Reply, Forward, Copy, Eye, EyeOff,
  MessageSquare, Users, Hash, Calendar, FileText, Image as ImageIcon
} from 'lucide-react';
import EmojiPicker from 'emoji-picker-react';
import { format, formatDistanceToNow } from 'date-fns';

// ...existing code from user prompt...

export default MessagingInterface;
