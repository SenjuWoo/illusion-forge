// Maker bridge for Koikatsu and Honey Select 2.
// Listens on 127.0.0.1 only while the game is running. Unity calls happen on
// the main thread. Method signatures that were not verified are not called:
// the refresh allowlist is the two zero-argument UpdateShape methods, plus
// ChangeSettingHair when it really has zero parameters.
// BepInEx writes the log. A failed catalog or screenshot is returned as JSON.

using System;
using System.Collections;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Threading;
using BepInEx;
using BepInEx.Logging;

namespace IllusionForge
{
    [BepInPlugin("local.illusionforge.makerbridge", "Illusion Forge Maker Bridge", "1.0.0")]
    public sealed class MakerBridgePlugin : BaseUnityPlugin
    {
        const int MaxLine = 1024 * 1024;
        static readonly string[] ColorKeys = { "baseColor", "startColor", "endColor", "topColor", "underColor" };
        static readonly BindingFlags Any = BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic;

        readonly ConcurrentQueue<Job> _jobs = new ConcurrentQueue<Job>();
        TcpListener _listener;
        Thread _thread;
        volatile bool _run;
        ManualLogSource _log;

        sealed class Job
        {
            public string Line;
            public ConcurrentQueue<string> Reply;
            public int State; // 0 queued, 1 running, 2 dropped before it started
        }

        void Start()
        {
            _log = Logger;
            int port = Config.Bind("Network", "Port", 47331, "Loopback TCP port. Other interfaces are not opened.").Value;
            _run = true;
            _thread = new Thread(() => Listen(port));
            _thread.IsBackground = true;
            _thread.Name = "IllusionForgeBridge";
            _thread.Start();
            _log.LogInfo("maker bridge listening on 127.0.0.1:" + port);
        }

        void OnDestroy()
        {
            _run = false;
            try { if (_listener != null) _listener.Stop(); } catch (Exception) { }
        }

        void Update()
        {
            Job job;
            int budget = 2;
            while (budget-- > 0 && _jobs.TryDequeue(out job))
            {
                // A client that already gave up must not have the change applied afterwards.
                if (Interlocked.CompareExchange(ref job.State, 1, 0) != 0)
                    continue;
                string response;
                try { response = Handle(job.Line); }
                catch (Exception ex) { response = Error("exception", ex.GetType().Name + ": " + ex.Message); }
                job.Reply.Enqueue(response);
            }
        }

        void Listen(int port)
        {
            try
            {
                _listener = new TcpListener(IPAddress.Loopback, port);
                _listener.Start();
                while (_run)
                {
                    TcpClient client = _listener.AcceptTcpClient();
                    try { Serve(client); }
                    catch (Exception ex)
                    {
                        // One bad client must not stop the listener for the rest of the session.
                        if (_log != null) _log.LogWarning("bridge client failed: " + ex.Message);
                    }
                    finally { client.Close(); }
                }
            }
            catch (Exception ex)
            {
                if (_run && _log != null) _log.LogError("bridge stopped: " + ex.Message);
            }
        }

        void Serve(TcpClient client)
        {
            client.ReceiveTimeout = 15000;
            client.SendTimeout = 15000;
            using (NetworkStream stream = client.GetStream())
            {
                string line = ReadLine(stream);
                var reply = new ConcurrentQueue<string>();
                var job = new Job { Line = line, Reply = reply };
                _jobs.Enqueue(job);
                string response = null;
                var until = DateTime.UtcNow.AddSeconds(20);
                while (DateTime.UtcNow < until)
                {
                    if (reply.TryDequeue(out response)) break;
                    Thread.Sleep(10);
                }
                if (response == null && Interlocked.CompareExchange(ref job.State, 2, 0) != 0)
                {
                    // The main thread already started this command. Wait for its result.
                    var extra = DateTime.UtcNow.AddSeconds(20);
                    while (DateTime.UtcNow < extra)
                    {
                        if (reply.TryDequeue(out response)) break;
                        Thread.Sleep(10);
                    }
                }
                if (response == null) response = Error("timeout", "the main thread did not answer within 20 seconds");
                byte[] raw = System.Text.Encoding.UTF8.GetBytes(response + "\n");
                stream.Write(raw, 0, raw.Length);
            }
        }

        static string ReadLine(NetworkStream stream)
        {
            var buffer = new MemoryStream();
            while (true)
            {
                int value = stream.ReadByte();
                if (value < 0) break;
                if (value == '\n') break;
                if (value == '\r') continue;
                buffer.WriteByte((byte)value);
                if (buffer.Length > MaxLine) throw new InvalidOperationException("line exceeds 1MB");
            }
            return System.Text.Encoding.UTF8.GetString(buffer.ToArray());
        }

        string Handle(string line)
        {
            object parsed = JsonMini.Parse(line);
            var root = parsed as Dictionary<string, object>;
            if (root == null) return Error("bad_request", "expected an object");
            string op = AsString(Get(root, "op"));
            if (op == "ping") return Ok(Map("op", "pong", "process", ProcessName(), "game", GameId()));
            if (op == "status") return Status();
            if (op == "apply") return Apply(root);
            if (op == "dump_catalog") return DumpCatalog();
            if (op == "screenshot") return Screenshot();
            return Error("unknown_op", op ?? "");
        }

        string Status()
        {
            Type maker = FindMakerApi();
            object inside = maker == null ? null : CallStatic(maker, "InsideMaker", null);
            object control = maker == null ? null : CallStatic(maker, "GetCharacterControl", null);
            var map = Map(
                "op", "status",
                "process", ProcessName(),
                "game", GameId(),
                "maker_type_found", maker != null,
                "inside_maker", inside,
                "character", control != null,
                "visual_checked", false
            );
            map["ok"] = true;
            return JsonMini.Write(map);
        }

        string Apply(Dictionary<string, object> root)
        {
            Type maker = FindMakerApi();
            if (maker == null) return Error("no_maker_api", "KKAPI.Maker.MakerAPI is not loaded");
            object control = CallStatic(maker, "GetCharacterControl", null);
            if (control == null) return Error("maker_closed", "the maker preview is not available");

            var applied = new List<object>();
            var skipped = new List<object>();
            object face = FirstFace(control);
            object body = FirstBody(control);
            object hair = FirstHair(control);

            object faceSpec = Get(root, "face_sliders");
            if (faceSpec is Dictionary<string, object>)
                ApplySliders((Dictionary<string, object>)faceSpec, face, "shapeValueFace", false, applied, skipped);
            object bodySpec = Get(root, "body_sliders");
            if (bodySpec is Dictionary<string, object>)
                ApplySliders((Dictionary<string, object>)bodySpec, body, "shapeValueBody", true, applied, skipped);

            if (Get(root, "hair_color") != null)
                PaintParts(hair, ColorOf(Get(root, "hair_color")), applied, skipped, "hair_color");
            if (Get(root, "eye_color") != null)
                PaintPupil(face, ColorOf(Get(root, "eye_color")), applied, skipped);
            if (Get(root, "eyebrow_color") != null)
                PaintMember(face, "eyebrowColor", ColorOf(Get(root, "eyebrow_color")), applied, skipped, "eyebrowColor");
            if (Get(root, "skin_color") != null)
                PaintSkin(body, ColorOf(Get(root, "skin_color")), applied, skipped);

            object name = Get(root, "name");
            if (name is Dictionary<string, object>)
                ApplyNames(control, (Dictionary<string, object>)name, applied, skipped);
            if (Get(root, "sex") != null)
                ApplySex(control, Get(root, "sex"), applied, skipped);

            var refresh = new List<object>();
            if (AppliedField(applied, "shapeValueFace") || AppliedField(applied, "eye_color") || AppliedField(applied, "eyebrow"))
                InvokeZeroArg(control, "UpdateShapeFaceValueFromCustom", refresh);
            if (AppliedField(applied, "shapeValueBody") || AppliedField(applied, "skin"))
                InvokeZeroArg(control, "UpdateShapeBodyValueFromCustom", refresh);
            if (AppliedField(applied, "hair_color"))
                InvokeZeroArg(control, "ChangeSettingHair", refresh);

            return JsonMini.Write(Map(
                "ok", true,
                "op", "apply",
                "game", GameId(),
                "applied", applied,
                "skipped", skipped,
                "refresh", refresh,
                "visual_checked", false
            ));
        }

        void ApplySliders(Dictionary<string, object> spec, object owner, string field, bool body, List<object> applied, List<object> skipped)
        {
            if (owner == null)
            {
                skipped.Add(Map("field", field, "reason", "the maker object was not found"));
                return;
            }
            object seq = Member(owner, field);
            if (seq == null)
            {
                skipped.Add(Map("field", field, "reason", "field was not found"));
                return;
            }
            foreach (var pair in spec)
            {
                int index;
                if (!TryIndex(pair.Key, body, out index))
                {
                    skipped.Add(Map("field", field + "." + pair.Key, "reason", "not a numeric index, or height on a game other than Koikatsu"));
                    continue;
                }
                try
                {
                    string error = SetAt(seq, index, Convert.ToSingle(pair.Value, System.Globalization.CultureInfo.InvariantCulture));
                    if (error == null) applied.Add(Map("field", field + "[" + index + "]", "value", pair.Value));
                    else skipped.Add(Map("field", field + "[" + index + "]", "reason", error));
                }
                catch (Exception ex)
                {
                    skipped.Add(Map("field", field + "." + pair.Key, "reason", ex.Message));
                }
            }
        }

        static bool AppliedField(List<object> applied, string prefix)
        {
            foreach (object item in applied)
            {
                var map = item as Dictionary<string, object>;
                if (map == null) continue;
                object field;
                if (map.TryGetValue("field", out field) && AsString(field).StartsWith(prefix, StringComparison.Ordinal))
                    return true;
            }
            return false;
        }

        static bool TryIndex(string key, bool body, out int index)
        {
            index = 0;
            if (body && key == "height")
            {
                if (GameId() != "kk") return false;
                index = 0;
                return true;
            }
            return int.TryParse(key, out index);
        }

        static string SetAt(object seq, int index, float value)
        {
            var array = seq as Array;
            if (array != null)
            {
                if (index < 0 || index >= array.Length) return "index outside 0.." + (array.Length - 1);
                Type elem = array.GetType().GetElementType();
                array.SetValue(Convert.ChangeType(value, elem), index);
                return null;
            }
            var list = seq as IList;
            if (list != null)
            {
                if (index < 0 || index >= list.Count) return "index outside 0.." + (list.Count - 1);
                list[index] = value;
                return null;
            }
            return "shape value is not a list";
        }

        static void PaintParts(object hair, float[] color, List<object> applied, List<object> skipped, string label)
        {
            if (hair == null) { skipped.Add(Map("field", label, "reason", "hair was not found")); return; }
            object parts = Member(hair, "parts");
            var list = AsList(parts);
            if (list.Count == 0) { skipped.Add(Map("field", label, "reason", "hair has no parts")); return; }
            var written = new List<object>();
            for (int i = 0; i < list.Count; i++)
            {
                foreach (string key in ColorKeys)
                {
                    if (PaintMember(list[i], key, color, applied, skipped, null))
                        written.Add("parts[" + i + "]." + key);
                }
            }
            if (written.Count == 0) skipped.Add(Map("field", label, "reason", "no hair color field was present"));
            else applied.Add(Map("field", label, "keys", written));
        }

        static void PaintPupil(object face, float[] color, List<object> applied, List<object> skipped)
        {
            if (face == null) { skipped.Add(Map("field", "eye_color", "reason", "face was not found")); return; }
            var list = AsList(Member(face, "pupil"));
            if (list.Count == 0 && Member(face, "pupil") != null) list.Add(Member(face, "pupil"));
            var written = new List<object>();
            for (int i = 0; i < list.Count; i++)
            {
                if (PaintMember(list[i], "baseColor", color, applied, skipped, null))
                    written.Add("pupil[" + i + "].baseColor");
            }
            if (written.Count == 0) skipped.Add(Map("field", "eye_color", "reason", "pupil baseColor was not found"));
            else applied.Add(Map("field", "eye_color", "keys", written));
        }

        static void PaintSkin(object body, float[] color, List<object> applied, List<object> skipped)
        {
            if (body == null) { skipped.Add(Map("field", "skin_color", "reason", "body was not found")); return; }
            bool any = false;
            foreach (string key in new[] { "skinMainColor", "skinColor", "skinSubColor" })
            {
                if (PaintMember(body, key, color, applied, skipped, null))
                {
                    any = true;
                    applied.Add(Map("field", key));
                }
            }
            if (!any) skipped.Add(Map("field", "skin_color", "reason", "no skin color field was present"));
        }

        static bool PaintMember(object owner, string field, float[] color, List<object> applied, List<object> skipped, string record)
        {
            if (owner == null) return false;
            MemberInfo info = FindMember(owner.GetType(), field);
            if (info == null) return false;
            try
            {
                object current = Read(owner, info);
                object next = MakeColor(current, MemberType(info), color);
                Write(owner, info, next);
                if (record != null) applied.Add(Map("field", record));
                return true;
            }
            catch (Exception ex)
            {
                skipped.Add(Map("field", field, "reason", ex.Message));
                return false;
            }
        }

        static object MakeColor(object current, Type type, float[] color)
        {
            if (current is IList && !(current is string))
            {
                var list = (IList)current;
                for (int i = 0; i < color.Length && i < list.Count; i++) list[i] = color[i];
                return current;
            }
            if (type == typeof(float[]) || (type != null && type.IsArray && type.GetElementType() == typeof(float)))
                return new float[] { color[0], color[1], color[2], color[3] };
            if (type != null && type.Name == "Color")
                return Activator.CreateInstance(type, color[0], color[1], color[2], color[3]);
            return new float[] { color[0], color[1], color[2], color[3] };
        }

        static float[] ColorOf(object value)
        {
            var list = value as IList;
            if (list == null || list.Count < 3) throw new FormatException("color needs 3 or 4 numbers");
            float r = Convert.ToSingle(list[0], System.Globalization.CultureInfo.InvariantCulture);
            float g = Convert.ToSingle(list[1], System.Globalization.CultureInfo.InvariantCulture);
            float b = Convert.ToSingle(list[2], System.Globalization.CultureInfo.InvariantCulture);
            float a = list.Count > 3 ? Convert.ToSingle(list[3], System.Globalization.CultureInfo.InvariantCulture) : 1f;
            // Match the Python writer: a channel above 1 is a 0-255 color, not a slider.
            if (r > 1f || g > 1f || b > 1f || a > 1f)
            {
                r /= 255f;
                g /= 255f;
                b /= 255f;
                a /= 255f;
            }
            return new[] { Clamp(r), Clamp(g), Clamp(b), Clamp(a) };
        }

        static float Clamp(float value)
        {
            if (value < 0f) return 0f;
            if (value > 1f) return 1f;
            return value;
        }

        static void ApplyNames(object control, Dictionary<string, object> name, List<object> applied, List<object> skipped)
        {
            object param = FindParameter(control);
            if (param == null) { skipped.Add(Map("field", "name", "reason", "parameter object was not found")); return; }
            foreach (string key in new[] { "lastname", "firstname", "nickname", "fullname" })
            {
                if (!name.ContainsKey(key) || name[key] == null || AsString(name[key]).Length == 0) continue;
                if (SetString(param, key, AsString(name[key]))) applied.Add(Map("field", "name." + key));
                else skipped.Add(Map("field", "name." + key, "reason", "field is not on the parameter object"));
            }
        }

        static void ApplySex(object control, object value, List<object> applied, List<object> skipped)
        {
            object param = FindParameter(control);
            if (param == null || !SetLoose(param, "sex", value))
                skipped.Add(Map("field", "sex", "reason", "sex field was not found"));
            else applied.Add(Map("field", "sex", "value", value));
        }

        static object FindParameter(object control)
        {
            object file = Member(control, "chaFile");
            foreach (string name in new[] { "parameter", "Parameter", "fileParam" })
            {
                object found = Member(file, name) ?? Member(control, name);
                if (found != null && (FindMember(found.GetType(), "lastname") != null || FindMember(found.GetType(), "fullname") != null || FindMember(found.GetType(), "sex") != null))
                    return found;
            }
            return null;
        }

        static void InvokeZeroArg(object target, string name, List<object> refresh)
        {
            if (target == null) { refresh.Add(Map("method", name, "called", false, "reason", "no target")); return; }
            MethodInfo match = null;
            int withArgs = 0;
            foreach (MethodInfo method in target.GetType().GetMethods(Any))
            {
                if (method.Name != name) continue;
                if (method.GetParameters().Length == 0) { match = method; break; }
                withArgs++;
            }
            if (match == null)
            {
                refresh.Add(Map("method", name, "called", false, "reason", withArgs > 0 ? "present but not zero-arg; not called" : "not found"));
                return;
            }
            match.Invoke(target, null);
            refresh.Add(Map("method", name, "called", true));
        }

        string DumpCatalog()
        {
            Type listType = FindTypeByName("ChaListControl");
            if (listType == null) return Error("no_catalog", "ChaListControl is not loaded");
            object instance = CallStatic(listType, "Instance", null) ?? CallStatic(listType, "instance", null);
            if (instance == null) return Error("no_catalog", "ChaListControl has no static Instance");
            MethodInfo method = null;
            foreach (MethodInfo candidate in listType.GetMethods(Any))
            {
                if (candidate.Name == "GetCategoryInfo" && candidate.GetParameters().Length == 1)
                {
                    method = candidate;
                    break;
                }
            }
            if (method == null) return Error("no_catalog", "GetCategoryInfo with one argument was not found");
            Type argType = method.GetParameters()[0].ParameterType;
            var categories = new List<object>();
            if (!argType.IsEnum) return Error("no_catalog", "GetCategoryInfo argument is " + argType.FullName + ", which this bridge does not call");
            int count = 0;
            foreach (object value in Enum.GetValues(argType))
            {
                if (count++ >= 24) break;
                try
                {
                    object info = method.Invoke(instance, new[] { value });
                    categories.Add(Map("category", value.ToString(), "items", DescribeList(info, 60)));
                }
                catch (Exception ex)
                {
                    categories.Add(Map("category", value.ToString(), "error", ex.InnerException != null ? ex.InnerException.Message : ex.Message));
                }
            }
            return JsonMini.Write(Map("ok", true, "op", "dump_catalog", "capped", true, "categories", categories, "visual_checked", false));
        }

        static List<object> DescribeList(object info, int cap)
        {
            var rows = new List<object>();
            foreach (object item in AsList(info))
            {
                if (rows.Count >= cap) break;
                if (item == null) continue;
                object id = Member(item, "Id") ?? Member(item, "id") ?? Member(item, "Category");
                object name = Member(item, "Name") ?? Member(item, "name") ?? Member(item, "AssetName");
                rows.Add(Map("id", id, "name", name, "type", item.GetType().Name));
            }
            if (rows.Count == 0 && info != null)
                rows.Add(Map("type", info.GetType().FullName, "note", "return value was not a list of items"));
            return rows;
        }

        string Screenshot()
        {
            string dir = Path.Combine(Paths.CachePath, "IllusionForge");
            Directory.CreateDirectory(dir);
            string file = Path.Combine(dir, "maker-" + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + ".png");
            Type capture = FindTypeByName("ScreenCapture");
            if (capture == null) return Error("no_screenshot", "UnityEngine.ScreenCapture is not loaded");
            MethodInfo method = null;
            foreach (MethodInfo candidate in capture.GetMethods(BindingFlags.Public | BindingFlags.Static))
            {
                ParameterInfo[] parameters = candidate.GetParameters();
                if (candidate.Name == "CaptureScreenshot" && parameters.Length == 1 && parameters[0].ParameterType == typeof(string))
                {
                    method = candidate;
                    break;
                }
            }
            if (method == null) return Error("no_screenshot", "CaptureScreenshot(string) was not found");
            method.Invoke(null, new object[] { file });
            return JsonMini.Write(Map(
                "ok", true,
                "op", "screenshot",
                "path", file,
                "note", "CaptureScreenshot writes at the end of the frame. The file may still be empty if you read it immediately.",
                "visual_checked", false
            ));
        }

        static object FirstFace(object control)
        {
            object file = Member(control, "chaFile");
            return Member(Member(Member(file, "custom"), "face"), "shapeValueFace") != null
                ? Member(Member(file, "custom"), "face")
                : Member(control, "fileFace");
        }

        static object FirstBody(object control)
        {
            object file = Member(control, "chaFile");
            object body = Member(Member(file, "custom"), "body");
            if (body != null && Member(body, "shapeValueBody") != null) return body;
            return Member(control, "fileBody");
        }

        static object FirstHair(object control)
        {
            object file = Member(control, "chaFile");
            object hair = Member(Member(file, "custom"), "hair");
            if (hair != null) return hair;
            return Member(control, "fileHair");
        }

        static Type FindMakerApi()
        {
            foreach (Assembly asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type[] types = SafeTypes(asm);
                for (int i = 0; i < types.Length; i++)
                {
                    Type type = types[i];
                    if (type != null && type.Name == "MakerAPI" && type.Namespace == "KKAPI.Maker") return type;
                }
            }
            return null;
        }

        static Type FindTypeByName(string name)
        {
            foreach (Assembly asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type[] types = SafeTypes(asm);
                for (int i = 0; i < types.Length; i++)
                {
                    Type type = types[i];
                    if (type != null && type.Name == name) return type;
                }
            }
            return null;
        }

        static Type[] SafeTypes(Assembly asm)
        {
            try { return asm.GetTypes(); }
            catch (ReflectionTypeLoadException ex) { return ex.Types ?? new Type[0]; }
            catch (Exception) { return new Type[0]; }
        }

        static object CallStatic(Type type, string name, object[] args)
        {
            int argc = args == null ? 0 : args.Length;
            PropertyInfo prop = type.GetProperty(name, BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic);
            if (prop != null && argc == 0) return prop.GetValue(null, null);
            FieldInfo field = type.GetField(name, BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic);
            if (field != null && argc == 0) return field.GetValue(null);
            foreach (MethodInfo method in type.GetMethods(BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic))
            {
                if (method.Name == name && method.GetParameters().Length == argc) return method.Invoke(null, args);
            }
            return null;
        }

        static object Member(object owner, string name)
        {
            if (owner == null) return null;
            MemberInfo info = FindMember(owner.GetType(), name);
            if (info == null) return null;
            return Read(owner, info);
        }

        static MemberInfo FindMember(Type type, string name)
        {
            const BindingFlags flags = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
            FieldInfo field = type.GetField(name, flags);
            if (field != null) return field;
            return type.GetProperty(name, flags);
        }

        static object Read(object owner, MemberInfo info)
        {
            var field = info as FieldInfo;
            if (field != null) return field.GetValue(owner);
            return ((PropertyInfo)info).GetValue(owner, null);
        }

        static void Write(object owner, MemberInfo info, object value)
        {
            var field = info as FieldInfo;
            if (field != null) field.SetValue(owner, value);
            else ((PropertyInfo)info).SetValue(owner, value, null);
        }

        static Type MemberType(MemberInfo info)
        {
            var field = info as FieldInfo;
            if (field != null) return field.FieldType;
            return ((PropertyInfo)info).PropertyType;
        }

        static bool SetString(object owner, string name, string value)
        {
            MemberInfo info = FindMember(owner.GetType(), name);
            if (info == null) return false;
            Write(owner, info, value);
            return true;
        }

        static bool SetLoose(object owner, string name, object value)
        {
            MemberInfo info = FindMember(owner.GetType(), name);
            if (info == null) return false;
            object current = Read(owner, info);
            object next = value;
            if (current is byte) next = Convert.ToByte(value);
            else if (current is int) next = Convert.ToInt32(value);
            else if (current is float) next = Convert.ToSingle(value);
            else if (current is bool) next = Convert.ToBoolean(value);
            Write(owner, info, next);
            return true;
        }

        static List<object> AsList(object value)
        {
            var result = new List<object>();
            if (value is string) return result;
            var list = value as IEnumerable;
            if (list == null) return result;
            foreach (object item in list) result.Add(item);
            return result;
        }

        static string ProcessName()
        {
            try { return System.Diagnostics.Process.GetCurrentProcess().ProcessName; }
            catch (Exception) { return ""; }
        }

        static string GameId()
        {
            string name = ProcessName();
            if (name.StartsWith("Koikatu", StringComparison.OrdinalIgnoreCase)) return "kk";
            if (name.StartsWith("HoneySelect2", StringComparison.OrdinalIgnoreCase)) return "hs2";
            return name;
        }

        static object Get(Dictionary<string, object> map, string key)
        {
            object value;
            return map.TryGetValue(key, out value) ? value : null;
        }

        static string AsString(object value)
        {
            return value == null ? "" : Convert.ToString(value, System.Globalization.CultureInfo.InvariantCulture);
        }

        static string Ok(Dictionary<string, object> map)
        {
            map["ok"] = true;
            return JsonMini.Write(map);
        }

        static string Error(string code, string message)
        {
            return JsonMini.Write(Map("ok", false, "error", code, "message", message, "visual_checked", false));
        }

        static Dictionary<string, object> Map(params object[] pairs)
        {
            var map = new Dictionary<string, object>();
            for (int i = 0; i + 1 < pairs.Length; i += 2)
                map[Convert.ToString(pairs[i])] = pairs[i + 1];
            return map;
        }
    }
}
