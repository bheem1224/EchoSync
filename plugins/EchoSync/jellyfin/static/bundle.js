//#region node_modules/svelte/src/internal/disclose-version.js
typeof window < "u" && ((window.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5");
//#endregion
//#region node_modules/svelte/src/internal/flags/index.js
var e = !1, t = !1;
function n() {
	t = !0;
}
//#endregion
//#region node_modules/svelte/src/internal/flags/legacy.js
n();
//#endregion
//#region node_modules/svelte/src/constants.js
var r = {}, i = Symbol("uninitialized"), a = "http://www.w3.org/1999/xhtml", o = Array.isArray, s = Array.prototype.indexOf, c = Array.prototype.includes, l = Array.from, u = Object.keys, d = Object.defineProperty, f = Object.getOwnPropertyDescriptor, p = Object.getOwnPropertyDescriptors, m = Object.prototype, h = Array.prototype, g = Object.getPrototypeOf, _ = Object.isExtensible, ee = () => {};
function te(e) {
	return e();
}
function v(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function ne() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var y = 1024, b = 2048, x = 4096, re = 8192, ie = 16384, ae = 32768, oe = 1 << 25, se = 65536, S = 1 << 19, ce = 1 << 20, C = 65536, le = 1 << 21, ue = 1 << 22, de = 1 << 23, fe = Symbol("$state"), pe = Symbol("legacy props"), me = Symbol(""), he = Symbol("attributes"), ge = Symbol("class"), _e = Symbol("style"), ve = Symbol("text"), ye = Symbol("form reset"), be = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), xe = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function Se(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
//#endregion
//#region node_modules/svelte/src/internal/client/errors.js
function Ce() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function we(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function Te() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function Ee(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function De() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function Oe() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function ke(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function Ae() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function je() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Me() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function Ne() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
function Pe() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function Fe(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function Ie() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/hydration.js
var w = !1;
function Le(e) {
	w = e;
}
var T;
function E(e) {
	if (e === null) throw Fe(), r;
	return T = e;
}
function Re() {
	return E(/* @__PURE__ */ sn(T));
}
function D(e) {
	if (w) {
		if (/* @__PURE__ */ sn(T) !== null) throw Fe(), r;
		T = e;
	}
}
function ze(e = 1) {
	if (w) {
		for (var t = e, n = T; t--;) n = /* @__PURE__ */ sn(n);
		T = n;
	}
}
function Be(e = !0) {
	for (var t = 0, n = T;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ sn(n);
		e && n.remove(), n = i;
	}
}
function Ve(e) {
	if (!e || e.nodeType !== 8) throw Fe(), r;
	return e.data;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/equality.js
function He(e) {
	return e === this.v;
}
function Ue(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function We(e) {
	return !Ue(e, this.v);
}
//#endregion
//#region node_modules/svelte/src/internal/client/context.js
var O = null;
function Ge(e) {
	O = e;
}
function Ke(e, n = !1, r) {
	O = {
		p: O,
		i: !1,
		c: null,
		e: null,
		s: e,
		x: null,
		r: G,
		l: t && !n ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function qe(e) {
	var t = O, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) xn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, O = t.p, e ?? {};
}
function Je() {
	return !t || O !== null && O.l === null;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/task.js
var Ye = [];
function Xe() {
	var e = Ye;
	Ye = [], v(e);
}
function Ze(e) {
	if (Ye.length === 0 && !ft) {
		var t = Ye;
		queueMicrotask(() => {
			t === Ye && Xe();
		});
	}
	Ye.push(e);
}
function Qe() {
	for (; Ye.length > 0;) Xe();
}
function $e(e) {
	var t = G;
	if (t === null) return H.f |= de, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	et(e, t);
}
function et(e, t) {
	for (; t !== null;) {
		if (t.f & 128) {
			if (!(t.f & 32768)) throw e;
			try {
				t.b.error(e);
				return;
			} catch (t) {
				e = t;
			}
		}
		t = t.parent;
	}
	throw e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/status.js
var tt = ~(b | x | y);
function k(e, t) {
	e.f = e.f & tt | t;
}
function nt(e) {
	e.f & 512 || e.deps === null ? k(e, y) : k(e, x);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/utils.js
function rt(e) {
	if (e !== null) for (let t of e) !(t.f & 2) || !(t.f & 65536) || (t.f ^= C, rt(t.deps));
}
function it(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), rt(e.deps), k(e, y);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/store.js
var at = !1, ot = !1;
function st(e) {
	var t = ot;
	try {
		return ot = !1, [e(), ot];
	} finally {
		ot = t;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/batch.js
var ct = null, lt = null, A = null, ut = null, j = null, dt = null, ft = !1, pt = !1, mt = null, ht = null, gt = 0, _t = 1, vt = class t {
	id = _t++;
	#e = !1;
	linked = !0;
	#t = null;
	#n = null;
	async_deriveds = /* @__PURE__ */ new Map();
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	unblocked = /* @__PURE__ */ new Set();
	#r = /* @__PURE__ */ new Set();
	#i = /* @__PURE__ */ new Set();
	#a = /* @__PURE__ */ new Set();
	#o = 0;
	#s = /* @__PURE__ */ new Map();
	#c = null;
	#l = [];
	#u = [];
	#d = /* @__PURE__ */ new Set();
	#f = /* @__PURE__ */ new Set();
	#p = /* @__PURE__ */ new Map();
	#m = /* @__PURE__ */ new Set();
	is_fork = !1;
	#h = !1;
	#g() {
		if (this.is_fork) return !0;
		for (let n of this.#s.keys()) {
			for (var e = n, t = !1; e.parent !== null;) {
				if (this.#p.has(e)) {
					t = !0;
					break;
				}
				e = e.parent;
			}
			if (!t) return !0;
		}
		return !1;
	}
	skip_effect(e) {
		this.#p.has(e) || this.#p.set(e, {
			d: [],
			m: []
		}), this.#m.delete(e);
	}
	unskip_effect(e, t = (e) => this.schedule(e)) {
		var n = this.#p.get(e);
		if (n) {
			this.#p.delete(e);
			for (var r of n.d) k(r, b), t(r);
			for (r of n.m) k(r, x), t(r);
		}
		this.#m.add(e);
	}
	#_() {
		if (this.#e = !0, gt++ > 1e3 && (this.#w(), bt()), !this.#g()) {
			for (let e of this.#d) this.#f.delete(e), k(e, b), this.schedule(e);
			for (let e of this.#f) k(e, x), this.schedule(e);
		}
		let n = this.#l;
		this.#l = [], this.apply();
		var r = mt = [], i = [], a = ht = [];
		for (let e of n) try {
			this.#v(e, r, i);
		} catch (t) {
			throw Et(e), t;
		}
		if (A = null, a.length > 0) {
			var o = t.ensure();
			for (let e of a) o.schedule(e);
		}
		if (mt = null, ht = null, this.#g()) {
			this.#x(i), this.#x(r);
			for (let [e, t] of this.#p) Tt(e, t);
			a.length > 0 && A.#_();
			return;
		}
		let s = this.#y();
		if (s) {
			s.#b(this);
			return;
		}
		this.#d.clear(), this.#f.clear();
		for (let e of this.#r) e(this);
		this.#r.clear(), ut = this, xt(i), xt(r), ut = null, this.#c?.resolve();
		var c = A;
		if (this.linked && this.#o === 0 && this.#w(), e && !this.linked && (this.#S(), A = c), this.#l.length > 0) {
			c === null && (c = this, this.#C());
			let e = c;
			e.#l.push(...this.#l.filter((t) => !e.#l.includes(t)));
		}
		c !== null && c.#_();
	}
	#v(t, n, r) {
		t.f ^= y;
		for (var i = t.first; i !== null;) {
			var a = i.f, o = (a & 96) != 0;
			if (!(o && a & 1024 || a & 8192 || this.#p.has(i)) && i.fn !== null) {
				o ? i.f ^= y : a & 4 ? n.push(i) : e && a & 16777224 ? r.push(i) : Xn(i) && (a & 16 && this.#f.add(i), tr(i));
				var s = i.first;
				if (s !== null) {
					i = s;
					continue;
				}
			}
			for (; i !== null;) {
				var c = i.next;
				if (c !== null) {
					i = c;
					break;
				}
				i = i.parent;
			}
		}
	}
	#y() {
		for (var e = this.#t; e !== null;) {
			if (!e.is_fork) {
				for (let [t, [, n]] of this.current) if (e.current.has(t) && !n) return e;
			}
			e = e.#t;
		}
		return null;
	}
	#b(e) {
		for (let [t, n] of e.current) !this.previous.has(t) && e.previous.has(t) && this.previous.set(t, e.previous.get(t)), this.current.set(t, n);
		for (let [t, n] of e.async_deriveds) {
			let e = this.async_deriveds.get(t);
			e && n.promise.then(e.resolve);
		}
		let t = (e) => {
			var n = e.reactions;
			if (n !== null) for (let e of n) {
				var r = e.f;
				if (r & 2) t(e);
				else {
					var i = e;
					r & 4194320 && !this.async_deriveds.has(i) && (this.#f.delete(i), k(i, b), this.schedule(i));
				}
			}
		};
		for (let e of this.current.keys()) t(e);
		this.oncommit(() => e.discard()), e.#w(), A = this, this.#_();
	}
	#x(e) {
		for (var t = 0; t < e.length; t += 1) it(e[t], this.#d, this.#f);
	}
	capture(e, t, n = !1) {
		e.v !== i && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), j?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		A = this;
	}
	deactivate() {
		A = null, j = null;
	}
	flush() {
		try {
			pt = !0, A = this, this.#_();
		} finally {
			gt = 0, dt = null, mt = null, ht = null, pt = !1, A = null, j = null, Gt.clear();
		}
	}
	discard() {
		for (let e of this.#i) e(this);
		this.#i.clear(), this.#a.clear(), this.#w();
	}
	register_created_effect(e) {
		this.#u.push(e);
	}
	#S() {
		this.#w();
		for (let l = ct; l !== null; l = l.#n) {
			var e = l.id < this.id, t = [];
			for (let [r, [i, a]] of this.current) {
				if (l.current.has(r)) {
					var n = l.current.get(r)[0];
					if (e && i !== n) l.current.set(r, [i, a]);
					else continue;
				}
				t.push(r);
			}
			if (e) for (let [e, t] of this.async_deriveds) {
				let n = l.async_deriveds.get(e);
				n && t.promise.then(n.resolve);
			}
			if (l.#e) {
				var r = [...l.current.keys()].filter((e) => !this.current.has(e));
				if (r.length === 0) e && l.discard();
				else if (t.length > 0) {
					if (e) for (let e of this.#m) l.unskip_effect(e, (e) => {
						e.f & 4194320 ? l.schedule(e) : l.#x([e]);
					});
					l.activate();
					var i = /* @__PURE__ */ new Set(), a = /* @__PURE__ */ new Map();
					for (var o of t) St(o, r, i, a);
					a = /* @__PURE__ */ new Map();
					var s = [...l.current.keys()].filter((e) => this.current.has(e) ? this.current.get(e)[0] !== e.v : !0);
					if (s.length > 0) for (let e of this.#u) !(e.f & 155648) && Ct(e, s, a) && (e.f & 4194320 ? (k(e, b), l.schedule(e)) : l.#d.add(e));
					if (l.#l.length > 0 && !l.#h) {
						l.apply();
						for (var c of l.#l) l.#v(c, [], []);
						l.#l = [];
					}
					l.deactivate();
				}
			}
		}
	}
	increment(e, t) {
		if (this.#o += 1, e) {
			let e = this.#s.get(t) ?? 0;
			this.#s.set(t, e + 1);
		}
	}
	decrement(e, t) {
		if (--this.#o, e) {
			let e = this.#s.get(t) ?? 0;
			e === 1 ? this.#s.delete(t) : this.#s.set(t, e - 1);
		}
		this.#h || (this.#h = !0, Ze(() => {
			this.#h = !1, this.linked && this.flush();
		}));
	}
	transfer_effects(e, t) {
		for (let t of e) this.#d.add(t);
		for (let e of t) this.#f.add(e);
		e.clear(), t.clear();
	}
	oncommit(e) {
		this.#r.add(e);
	}
	ondiscard(e) {
		this.#i.add(e);
	}
	on_fork_commit(e) {
		this.#a.add(e);
	}
	run_fork_commit_callbacks() {
		for (let e of this.#a) e(this);
		this.#a.clear();
	}
	settled() {
		return (this.#c ??= ne()).promise;
	}
	static ensure() {
		if (A === null) {
			let e = A = new t();
			e.#C(), !pt && !ft && Ze(() => {
				e.#e || e.flush();
			});
		}
		return A;
	}
	apply() {
		if (!e || !this.is_fork && this.#t === null && this.#n === null) {
			j = null;
			return;
		}
		j = /* @__PURE__ */ new Map();
		for (let [e, [t]] of this.current) j.set(e, t);
		for (let e = ct; e !== null; e = e.#n) if (!(e === this || e.is_fork)) {
			var t = !1;
			if (e.id < this.id) {
				for (let [n, [, r]] of e.current) if (!r && this.current.has(n)) {
					t = !0;
					break;
				}
			}
			if (!t) for (let [t, n] of e.previous) j.has(t) || j.set(t, n);
		}
	}
	schedule(t) {
		if (dt = t, t.b?.is_pending && t.f & 16777228 && !(t.f & 32768)) {
			t.b.defer_effect(t);
			return;
		}
		for (var n = t; n.parent !== null;) {
			n = n.parent;
			var r = n.f;
			if (mt !== null && n === G && (e || (H === null || !(H.f & 2)) && !at)) return;
			if (r & 96) {
				if (!(r & 1024)) return;
				n.f ^= y;
			}
		}
		this.#l.push(n);
	}
	#C() {
		lt === null ? ct = lt = this : (lt.#n = this, this.#t = lt), lt = this;
	}
	#w() {
		var e = this.#t, t = this.#n;
		e === null ? ct = t : e.#n = t, t === null ? lt = e : t.#t = e, this.linked = !1;
	}
};
function yt(e) {
	var t = ft;
	ft = !0;
	try {
		var n;
		for (e && (A !== null && !A.is_fork && A.flush(), n = e());;) {
			if (Qe(), A === null) return n;
			A.flush();
		}
	} finally {
		ft = t;
	}
}
function bt() {
	try {
		De();
	} catch (e) {
		et(e, dt);
	}
}
var M = null;
function xt(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && Xn(r) && (M = /* @__PURE__ */ new Set(), tr(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && Pn(r), M?.size > 0)) {
				Gt.clear();
				for (let e of M) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) M.has(n) && (M.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || tr(n);
					}
				}
				M.clear();
			}
		}
		M = null;
	}
}
function St(e, t, n, r) {
	if (!n.has(e) && (n.add(e), e.reactions !== null)) for (let i of e.reactions) {
		let e = i.f;
		e & 2 ? St(i, t, n, r) : e & 4194320 && !(e & 2048) && Ct(i, t, r) && (k(i, b), wt(i));
	}
}
function Ct(e, t, n) {
	let r = n.get(e);
	if (r !== void 0) return r;
	if (e.deps !== null) for (let r of e.deps) {
		if (c.call(t, r)) return !0;
		if (r.f & 2 && Ct(r, t, n)) return n.set(r, !0), !0;
	}
	return n.set(e, !1), !1;
}
function wt(e) {
	A.schedule(e);
}
function Tt(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), k(e, y);
		for (var n = e.first; n !== null;) Tt(n, t), n = n.next;
	}
}
function Et(e) {
	k(e, y);
	for (var t = e.first; t !== null;) Et(t), t = t.next;
}
//#endregion
//#region node_modules/svelte/src/reactivity/create-subscriber.js
function Dt(e) {
	let t = 0, n = qt(0), r;
	return () => {
		vn() && (Z(n), Dn(() => (t === 0 && (r = ar(() => e(() => Xt(n)))), t += 1, () => {
			Ze(() => {
				--t, t === 0 && (r?.(), r = void 0, Xt(n));
			});
		})));
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var Ot = se | S;
function kt(e, t, n, r) {
	new At(e, t, n, r);
}
var At = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = w ? T : null;
	#n;
	#r;
	#i;
	#a = null;
	#o = null;
	#s = null;
	#c = null;
	#l = 0;
	#u = 0;
	#d = !1;
	#f = /* @__PURE__ */ new Set();
	#p = /* @__PURE__ */ new Set();
	#m = null;
	#h = Dt(() => (this.#m = qt(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = G;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = G.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = kn(() => {
			if (w) {
				let e = this.#t;
				Re();
				let t = e.data === "[!";
				if (e.data.startsWith("[?")) {
					let t = JSON.parse(e.data.slice(2));
					this.#_(t);
				} else t ? this.#v() : this.#g();
			} else this.#y();
		}, Ot), w && (this.#e = T);
	}
	#g() {
		try {
			this.#a = z(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed;
		t && (this.#s = z(() => {
			t(this.#e, () => e, () => () => {});
		}));
	}
	#v() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = z(() => e(this.#e)), Ze(() => {
			var e = this.#c = document.createDocumentFragment(), t = an();
			e.append(t), this.#a = this.#x(() => z(() => this.#r(t))), this.#u === 0 && (this.#e.before(e), this.#c = null, Fn(this.#o, () => {
				this.#o = null;
			}), this.#b(A));
		}));
	}
	#y() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = z(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				zn(this.#a, e);
				let t = this.#n.pending;
				this.#o = z(() => t(this.#e));
			} else this.#b(A);
		} catch (e) {
			this.error(e);
		}
	}
	#b(e) {
		this.is_pending = !1, e.transfer_effects(this.#f, this.#p);
	}
	defer_effect(e) {
		it(e, this.#f, this.#p);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#x(e) {
		var t = G, n = H, r = O;
		K(this.#i), W(this.#i), Ge(this.#i.ctx);
		try {
			return vt.ensure(), e();
		} catch (e) {
			return $e(e), null;
		} finally {
			K(t), W(n), Ge(r);
		}
	}
	#S(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#S(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#b(t), this.#o && Fn(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#S(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, Ze(() => {
			this.#d = !1, this.#m && Jt(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), Z(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		A?.is_fork ? (this.#a && A.skip_effect(this.#a), this.#o && A.skip_effect(this.#o), this.#s && A.skip_effect(this.#s), A.on_fork_commit(() => {
			this.#C(e);
		})) : this.#C(e);
	}
	#C(e) {
		this.#a &&= (B(this.#a), null), this.#o &&= (B(this.#o), null), this.#s &&= (B(this.#s), null), w && (E(this.#t), ze(), E(Be()));
		var t = this.#n.onerror;
		let n = this.#n.failed;
		var r = !1, i = !1;
		let a = () => {
			if (r) {
				Ie();
				return;
			}
			r = !0, i && Ne(), this.#s !== null && Fn(this.#s, () => {
				this.#s = null;
			}), this.#x(() => {
				this.#y();
			});
		}, o = (e) => {
			try {
				i = !0, t?.(e, a), i = !1;
			} catch (e) {
				et(e, this.#i && this.#i.parent);
			}
			n && (this.#s = this.#x(() => {
				try {
					return z(() => {
						var t = G;
						t.b = this, t.f |= 128, n(this.#e, () => e, () => a);
					});
				} catch (e) {
					return et(e, this.#i.parent), null;
				}
			}));
		};
		Ze(() => {
			var t;
			try {
				t = this.transform_error(e);
			} catch (e) {
				et(e, this.#i && this.#i.parent);
				return;
			}
			typeof t == "object" && t && typeof t.then == "function" ? t.then(o, (e) => et(e, this.#i && this.#i.parent)) : o(t);
		});
	}
};
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/async.js
function jt(e, t, n, r) {
	let i = Je() ? Ft : Rt;
	var a = e.filter((e) => !e.settled);
	if (n.length === 0 && a.length === 0) {
		r(t.map(i));
		return;
	}
	var o = G, s = Mt(), c = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function l(e) {
		if (!(o.f & 16384)) {
			s();
			try {
				r(e);
			} catch (e) {
				et(e, o);
			}
			Nt();
		}
	}
	var u = Pt();
	if (n.length === 0) {
		c.then(() => l(t.map(i))).finally(u);
		return;
	}
	function d() {
		Promise.all(n.map((e) => /* @__PURE__ */ Lt(e))).then((e) => l([...t.map(i), ...e])).catch((e) => et(e, o)).finally(u);
	}
	c ? c.then(() => {
		s(), d(), Nt();
	}) : d();
}
function Mt() {
	var e = G, t = H, n = O, r = A;
	return function(i = !0) {
		K(e), W(t), Ge(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function Nt(e = !0) {
	K(null), W(null), Ge(null), e && A?.deactivate();
}
function Pt() {
	var e = G, t = e.b, n = A, r = t.is_rendered();
	return t.update_pending_count(1, n), n.increment(r, e), () => {
		t.update_pending_count(-1, n), n.decrement(r, e);
	};
}
/* @__NO_SIDE_EFFECTS__ */
function Ft(e) {
	var t = 2 | b;
	return G !== null && (G.f |= S), {
		ctx: O,
		deps: null,
		effects: null,
		equals: He,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: i,
		wv: 0,
		parent: G,
		ac: null
	};
}
var It = Symbol("obsolete");
/* @__NO_SIDE_EFFECTS__ */
function Lt(e, t, n) {
	let r = G;
	r === null && Ce();
	var a = void 0, o = qt(i), s = !H, c = /* @__PURE__ */ new Set();
	return En(() => {
		var t = G, n = ne();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, (e) => {
				e !== be && n.reject(e);
			}).finally(Nt);
		} catch (e) {
			n.reject(e), Nt();
		}
		var i = A;
		if (s) {
			if (t.f & 32768) var l = Pt();
			if (r.b.is_rendered()) i.async_deriveds.get(t)?.reject(It);
			else for (let e of c.values()) e.reject(It);
			c.add(n), i.async_deriveds.set(t, n);
		}
		let u = (e, t = void 0) => {
			l?.(), c.delete(n), t !== It && (i.activate(), t ? (o.f |= de, Jt(o, t)) : (o.f & 8388608 && (o.f ^= de), Jt(o, e)), i.deactivate());
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), yn(() => {
		for (let e of c) e.reject(It);
	}), new Promise((e) => {
		function t(n) {
			function r() {
				n === a ? e(o) : t(a);
			}
			n.then(r, r);
		}
		t(a);
	});
}
/* @__NO_SIDE_EFFECTS__ */
function Rt(e) {
	let t = /* @__PURE__ */ Ft(e);
	return t.equals = We, t;
}
function zt(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) B(t[n]);
	}
}
function Bt(e) {
	var t, n = G, r = e.parent;
	if (!V && r !== null && e.v !== i && r.f & 24576) return Pe(), e.v;
	K(r);
	try {
		e.f &= ~C, zt(e), t = Qn(e);
	} finally {
		K(n);
	}
	return t;
}
function Vt(e) {
	var t = Bt(e);
	if (!e.equals(t) && (e.wv = Yn(), (!A?.is_fork || e.deps === null) && (A === null ? e.v = t : (A.capture(e, t, !0), ut?.capture(e, t, !0)), e.deps === null))) {
		k(e, y);
		return;
	}
	V || (j === null ? nt(e) : (vn() || A?.is_fork) && j.set(e, t));
}
function Ht(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac?.abort(be), t.fn !== null && (t.teardown = ee), t.ac = null, er(t, 0), jn(t));
}
function Ut(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && tr(t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/sources.js
var Wt = /* @__PURE__ */ new Set(), Gt = /* @__PURE__ */ new Map(), Kt = !1;
function qt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: He,
		rv: 0,
		wv: 0
	};
}
/* @__NO_SIDE_EFFECTS__ */
function N(e, t) {
	let n = qt(e, t);
	return Un(n), n;
}
/* @__NO_SIDE_EFFECTS__ */
function P(e, n = !1, r = !0) {
	let i = qt(e);
	return n || (i.equals = We), t && r && O !== null && O.l !== null && (O.l.s ??= []).push(i), i;
}
function F(e, t, n = !1) {
	return H !== null && (!U || H.f & 131072) && Je() && H.f & 4325394 && (q === null || !c.call(q, e)) && Me(), Jt(e, n ? Qt(t) : t, ht);
}
function Jt(e, t, n = null) {
	if (!e.equals(t)) {
		Gt.set(e, V ? t : e.v);
		var r = vt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && Bt(t), j === null && nt(t);
		}
		e.wv = Yn(), Zt(e, b, n), Je() && G !== null && G.f & 1024 && !(G.f & 96) && (X === null ? Wn([e]) : X.push(e)), !r.is_fork && Wt.size > 0 && !Kt && Yt();
	}
	return t;
}
function Yt() {
	Kt = !1;
	for (let e of Wt) {
		e.f & 1024 && k(e, x);
		let t;
		try {
			t = Xn(e);
		} catch {
			t = !0;
		}
		t && tr(e);
	}
	Wt.clear();
}
function Xt(e) {
	F(e, e.v + 1);
}
function Zt(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = Je(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (!(!i && s === G)) {
			var l = (c & b) === 0;
			if (l && k(s, t), c & 131072) Wt.add(s);
			else if (c & 2) {
				var u = s;
				j?.delete(u), c & 65536 || (c & 512 && (G === null || !(G.f & 2097152)) && (s.f |= C), Zt(u, x, n));
			} else if (l) {
				var d = s;
				c & 16 && M !== null && M.add(d), n === null ? wt(d) : n.push(d);
			}
		}
	}
}
function Qt(e) {
	if (typeof e != "object" || !e || fe in e) return e;
	let t = g(e);
	if (t !== m && t !== h) return e;
	var n = /* @__PURE__ */ new Map(), r = o(e), a = /* @__PURE__ */ N(0), s = null, c = qn, l = (e) => {
		if (qn === c) return e();
		var t = H, n = qn;
		W(null), Jn(c);
		var r = e();
		return W(t), Jn(n), r;
	};
	return r && n.set("length", /* @__PURE__ */ N(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && Ae();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ N(r.value, s);
				return n.set(t, e), e;
			}) : F(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var r = n.get(t);
			if (r === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ N(i, s));
					n.set(t, e), Xt(a);
				}
			} else F(r, i), Xt(a);
			return !0;
		},
		get(t, r, a) {
			if (r === fe) return e;
			var o = n.get(r), c = r in t;
			if (o === void 0 && (!c || f(t, r)?.writable) && (o = l(() => /* @__PURE__ */ N(Qt(c ? t[r] : i), s)), n.set(r, o)), o !== void 0) {
				var u = Z(o);
				return u === i ? void 0 : u;
			}
			return Reflect.get(t, r, a);
		},
		getOwnPropertyDescriptor(e, t) {
			var r = Reflect.getOwnPropertyDescriptor(e, t);
			if (r && "value" in r) {
				var a = n.get(t);
				a && (r.value = Z(a));
			} else if (r === void 0) {
				var o = n.get(t), s = o?.v;
				if (o !== void 0 && s !== i) return {
					enumerable: !0,
					configurable: !0,
					value: s,
					writable: !0
				};
			}
			return r;
		},
		has(e, t) {
			if (t === fe) return !0;
			var r = n.get(t), a = r !== void 0 && r.v !== i || Reflect.has(e, t);
			return (r !== void 0 || G !== null && (!a || f(e, t)?.writable)) && (r === void 0 && (r = l(() => /* @__PURE__ */ N(a ? Qt(e[t]) : i, s)), n.set(t, r)), Z(r) === i) ? !1 : a;
		},
		set(e, t, o, c) {
			var u = n.get(t), d = t in e;
			if (r && t === "length") for (var p = o; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ N(i, s)), n.set(p + "", m)) : F(m, i);
			}
			if (u === void 0) (!d || f(e, t)?.writable) && (u = l(() => /* @__PURE__ */ N(void 0, s)), F(u, Qt(o)), n.set(t, u));
			else {
				d = u.v !== i;
				var h = l(() => Qt(o));
				F(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, o), !d) {
				if (r && typeof t == "string") {
					var _ = n.get("length"), ee = Number(t);
					Number.isInteger(ee) && ee >= _.v && F(_, ee + 1);
				}
				Xt(a);
			}
			return !0;
		},
		ownKeys(e) {
			Z(a);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== i;
			});
			for (var [r, o] of n) o.v !== i && !(r in e) && t.push(r);
			return t;
		},
		setPrototypeOf() {
			je();
		}
	});
}
new Set([
	"copyWithin",
	"fill",
	"pop",
	"push",
	"reverse",
	"shift",
	"sort",
	"splice",
	"unshift"
]);
var $t, en, tn, nn;
function rn() {
	if ($t === void 0) {
		$t = window, en = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		tn = f(t, "firstChild").get, nn = f(t, "nextSibling").get, _(e) && (e[ge] = void 0, e[he] = null, e[_e] = void 0, e.__e = void 0), _(n) && (n[ve] = void 0);
	}
}
function an(e = "") {
	return document.createTextNode(e);
}
/* @__NO_SIDE_EFFECTS__ */
function on(e) {
	return tn.call(e);
}
/* @__NO_SIDE_EFFECTS__ */
function sn(e) {
	return nn.call(e);
}
function I(e, t) {
	if (!w) return /* @__PURE__ */ on(e);
	var n = /* @__PURE__ */ on(T);
	if (n === null) n = T.appendChild(an());
	else if (t && n.nodeType !== 3) {
		var r = an();
		return n?.before(r), E(r), r;
	}
	return t && dn(n), E(n), n;
}
function L(e, t = 1, n = !1) {
	let r = w ? T : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ sn(r);
	if (!w) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = an();
			return r === null ? i?.after(a) : r.before(a), E(a), a;
		}
		dn(r);
	}
	return E(r), r;
}
function cn(e) {
	e.textContent = "";
}
function ln() {
	return !e || M !== null ? !1 : (G.f & ae) !== 0;
}
function un(e, t, n) {
	let r = n ? { is: n } : void 0;
	return document.createElementNS(t ?? "http://www.w3.org/1999/xhtml", e, r);
}
function dn(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var fn = !1;
function pn() {
	fn || (fn = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[ye]?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function mn(e) {
	var t = H, n = G;
	W(null), K(null);
	try {
		return e();
	} finally {
		W(t), K(n);
	}
}
function hn(e, t, n, r = n) {
	e.addEventListener(t, () => mn(n));
	let i = e[ye];
	i ? e[ye] = () => {
		i(), r(!0);
	} : e[ye] = () => r(!0), pn();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function gn(e) {
	G === null && (H === null && Ee(e), Te()), V && we(e);
}
function _n(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function R(e, t) {
	var n = G;
	n !== null && n.f & 8192 && (e |= re);
	var r = {
		ctx: O,
		deps: null,
		nodes: null,
		f: e | b | 512,
		first: null,
		fn: t,
		last: null,
		next: null,
		parent: n,
		b: n && n.b,
		prev: null,
		teardown: null,
		wv: 0,
		ac: null
	};
	A?.register_created_effect(r);
	var i = r;
	if (e & 4) mt === null ? vt.ensure().schedule(r) : mt.push(r);
	else if (t !== null) {
		try {
			tr(r);
		} catch (e) {
			throw B(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= se));
	}
	if (i !== null && (i.parent = n, n !== null && _n(i, n), H !== null && H.f & 2 && !(e & 64))) {
		var a = H;
		(a.effects ??= []).push(i);
	}
	return r;
}
function vn() {
	return H !== null && !U;
}
function yn(e) {
	let t = R(8, null);
	return k(t, y), t.teardown = e, t;
}
function bn(e) {
	gn("$effect");
	var t = G.f;
	if (!H && t & 32 && !(t & 32768)) {
		var n = O;
		(n.e ??= []).push(e);
	} else return xn(e);
}
function xn(e) {
	return R(4 | ce, e);
}
function Sn(e) {
	return gn("$effect.pre"), R(8 | ce, e);
}
function Cn(e) {
	vt.ensure();
	let t = R(64 | S, e);
	return () => {
		B(t);
	};
}
function wn(e) {
	vt.ensure();
	let t = R(64 | S, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? Fn(t, () => {
			B(t), n(void 0);
		}) : (B(t), n(void 0));
	});
}
function Tn(e) {
	return R(4, e);
}
function En(e) {
	return R(ue | S, e);
}
function Dn(e, t = 0) {
	return R(8 | t, e);
}
function On(e, t = [], n = [], r = []) {
	jt(r, t, n, (t) => {
		R(8, () => e(...t.map(Z)));
	});
}
function kn(e, t = 0) {
	return R(16 | t, e);
}
function z(e) {
	return R(32 | S, e);
}
function An(e) {
	var t = e.teardown;
	if (t !== null) {
		let e = V, n = H;
		Hn(!0), W(null);
		try {
			t.call(null);
		} finally {
			Hn(e), W(n);
		}
	}
}
function jn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && mn(() => {
			e.abort(be);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : B(n, t), n = r;
	}
}
function Mn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || B(t), t = n;
	}
}
function B(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (Nn(e.nodes.start, e.nodes.end), n = !0), k(e, oe), jn(e, t && !n), er(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	An(e), e.f ^= oe, e.f |= ie;
	var i = e.parent;
	i !== null && i.first !== null && Pn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function Nn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ sn(e);
		e.remove(), e = n;
	}
}
function Pn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function Fn(e, t, n = !0) {
	var r = [];
	In(e, r, !0);
	var i = () => {
		n && B(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function In(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= re;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = (i.f & 65536) != 0 || (i.f & 32) != 0 && (e.f & 16) != 0;
				In(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function Ln(e) {
	Rn(e, !0);
}
function Rn(e, t) {
	if (e.f & 8192) {
		e.f ^= re, e.f & 1024 || (k(e, b), vt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = (n.f & 65536) != 0 || (n.f & 32) != 0;
			Rn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function zn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ sn(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var Bn = null, Vn = !1, V = !1;
function Hn(e) {
	V = e;
}
var H = null, U = !1;
function W(e) {
	H = e;
}
var G = null;
function K(e) {
	G = e;
}
var q = null;
function Un(t) {
	H !== null && (!e || H.f & 2) && (q === null ? q = [t] : q.push(t));
}
var J = null, Y = 0, X = null;
function Wn(e) {
	X = e;
}
var Gn = 1, Kn = 0, qn = Kn;
function Jn(e) {
	qn = e;
}
function Yn() {
	return ++Gn;
}
function Xn(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~C), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (Xn(a) && Vt(a), a.wv > e.wv) return !0;
		}
		t & 512 && j === null && k(e, y);
	}
	return !1;
}
function Zn(t, n, r = !0) {
	var i = t.reactions;
	if (i !== null && !(!e && q !== null && c.call(q, t))) for (var a = 0; a < i.length; a++) {
		var o = i[a];
		o.f & 2 ? Zn(o, n, !1) : n === o && (r ? k(o, b) : o.f & 1024 && k(o, x), wt(o));
	}
}
function Qn(e) {
	var t = J, n = Y, r = X, i = H, a = q, o = O, s = U, c = qn, l = e.f;
	J = null, Y = 0, X = null, H = l & 96 ? null : e, q = null, Ge(e.ctx), U = !1, qn = ++Kn, e.ac !== null && (mn(() => {
		e.ac.abort(be);
	}), e.ac = null);
	try {
		e.f |= le;
		var u = e.fn, d = u();
		e.f |= ae;
		var f = e.deps, p = A?.is_fork;
		if (J !== null) {
			var m;
			if (p || er(e, Y), f !== null && Y > 0) for (f.length = Y + J.length, m = 0; m < J.length; m++) f[Y + m] = J[m];
			else e.deps = f = J;
			if (vn() && e.f & 512) for (m = Y; m < f.length; m++) (f[m].reactions ??= []).push(e);
		} else !p && f !== null && Y < f.length && (er(e, Y), f.length = Y);
		if (Je() && X !== null && !U && f !== null && !(e.f & 6146)) for (m = 0; m < X.length; m++) Zn(X[m], e);
		if (i !== null && i !== e) {
			if (Kn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Kn;
			if (t !== null) for (let e of t) e.rv = Kn;
			X !== null && (r === null ? r = X : r.push(...X));
		}
		return e.f & 8388608 && (e.f ^= de), d;
	} catch (e) {
		return $e(e);
	} finally {
		e.f ^= le, J = t, Y = n, X = r, H = i, q = a, Ge(o), U = s, qn = c;
	}
}
function $n(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var r = s.call(n, e);
		if (r !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[r] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (J === null || !c.call(J, t))) {
		var o = t;
		o.f & 512 && (o.f ^= 512, o.f &= ~C), o.v !== i && nt(o), Ht(o), er(o, 0);
	}
}
function er(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) $n(e, n[r]);
}
function tr(e) {
	var t = e.f;
	if (!(t & 16384)) {
		k(e, y);
		var n = G, r = Vn;
		G = e, Vn = !0;
		try {
			t & 16777232 ? Mn(e) : jn(e), An(e);
			var i = Qn(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = Gn;
		} finally {
			Vn = r, G = n;
		}
	}
}
async function nr() {
	if (e) return new Promise((e) => {
		requestAnimationFrame(() => e()), setTimeout(() => e());
	});
	await Promise.resolve(), yt();
}
function Z(e) {
	var t = (e.f & 2) != 0;
	if (Bn?.add(e), H !== null && !U && !(G !== null && G.f & 16384) && (q === null || !c.call(q, e))) {
		var n = H.deps;
		if (H.f & 2097152) e.rv < Kn && (e.rv = Kn, J === null && n !== null && n[Y] === e ? Y++ : J === null ? J = [e] : J.push(e));
		else {
			H.deps ??= [], c.call(H.deps, e) || H.deps.push(e);
			var r = e.reactions;
			r === null ? e.reactions = [H] : c.call(r, H) || r.push(H);
		}
	}
	if (V && Gt.has(e)) return Gt.get(e);
	if (t) {
		var i = e;
		if (V) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || ir(i)) && (a = Bt(i)), Gt.set(i, a), a;
		}
		var o = (i.f & 512) == 0 && !U && H !== null && (Vn || (H.f & 512) != 0), s = (i.f & ae) === 0;
		Xn(i) && (o && (i.f |= 512), Vt(i)), o && !s && (Ut(i), rr(i));
	}
	if (j?.has(e)) return j.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function rr(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (Ut(t), rr(t));
}
function ir(e) {
	if (e.v === i) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (Gt.has(t) || t.f & 2 && ir(t)) return !0;
	return !1;
}
function ar(e) {
	var t = U;
	try {
		return U = !0, e();
	} finally {
		U = t;
	}
}
function or(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (fe in e) sr(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && fe in n && sr(n);
		}
	}
}
function sr(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			sr(e[n], t);
		} catch {}
		let n = g(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = p(n);
			for (let n in t) {
				let r = t[n].get;
				if (r) try {
					r.call(e);
				} catch {}
			}
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/events.js
var cr = Symbol("events"), lr = /* @__PURE__ */ new Set(), ur = /* @__PURE__ */ new Set();
function dr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || mr.call(t, e), !e.cancelBubble) return mn(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? Ze(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function fr(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = dr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && yn(() => {
		t.removeEventListener(e, o, a);
	});
}
var pr = null;
function mr(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	pr = e;
	var o = 0, s = pr === e && e[cr];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[cr] = t;
			return;
		}
		var l = i.indexOf(t);
		if (l === -1) return;
		c <= l && (o = c);
	}
	if (a = i[o] || e.target, a !== t) {
		d(e, "currentTarget", {
			configurable: !0,
			get() {
				return a || n;
			}
		});
		var u = H, f = G;
		W(null), K(null);
		try {
			for (var p, m = []; a !== null;) {
				var h = a.assignedSlot || a.parentNode || a.host || null;
				try {
					var g = a[cr]?.[r];
					g != null && (!a.disabled || e.target === a) && g.call(a, e);
				} catch (e) {
					p ? m.push(e) : p = e;
				}
				if (e.cancelBubble || h === t || h === null) break;
				a = h;
			}
			if (p) {
				for (let e of m) queueMicrotask(() => {
					throw e;
				});
				throw p;
			}
		} finally {
			e[cr] = t, delete e.currentTarget, W(u), K(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var hr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function gr(e) {
	return hr?.createHTML(e) ?? e;
}
function _r(e) {
	var t = un("template");
	return t.innerHTML = gr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function vr(e, t) {
	var n = G;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/* @__NO_SIDE_EFFECTS__ */
function Q(e, t) {
	var n = (t & 1) != 0, r = (t & 2) != 0, i, a = !e.startsWith("<!>");
	return () => {
		if (w) return vr(T, null), T;
		i === void 0 && (i = _r(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ on(i)));
		var t = r || en ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ on(t), s = t.lastChild;
			vr(o, s);
		} else vr(t, t);
		return t;
	};
}
function $(e, t) {
	if (w) {
		var n = G;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = T), Re();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var yr = ["touchstart", "touchmove"];
function br(e) {
	return yr.includes(e);
}
function xr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[ve] ??= e.nodeValue) && (e[ve] = n, e.nodeValue = `${n}`);
}
function Sr(e, t) {
	return Tr(e, t);
}
function Cr(e, t) {
	rn(), t.intro = t.intro ?? !1;
	let n = t.target, i = w, a = T;
	try {
		for (var o = /* @__PURE__ */ on(n); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ sn(o);
		if (!o) throw r;
		Le(!0), E(o);
		let i = Tr(e, {
			...t,
			anchor: o
		});
		return Le(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== r && console.warn("Failed to hydrate: ", i), t.recover === !1 && Oe(), rn(), cn(n), Le(!1), Sr(e, t);
	} finally {
		Le(i), E(a);
	}
}
var wr = /* @__PURE__ */ new Map();
function Tr(e, { target: t, anchor: n, props: i = {}, events: a, context: o, intro: s = !0, transformError: c }) {
	rn();
	var u = void 0, d = wn(() => {
		var s = n ?? t.appendChild(an());
		kt(s, { pending: () => {} }, (t) => {
			Ke({});
			var n = O;
			if (o && (n.c = o), a && (i.$$events = a), w && vr(t, null), u = e(t, i) || {}, w && (G.nodes.end = T, T === null || T.nodeType !== 8 || T.data !== "]")) throw Fe(), r;
			qe();
		}, c);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = br(r);
					for (let e of [t, document]) {
						var a = wr.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), wr.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, mr, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(l(lr)), ur.add(f), () => {
			for (var e of d) for (let n of [t, document]) {
				var r = wr.get(n), i = r.get(e);
				--i == 0 ? (n.removeEventListener(e, mr), r.delete(e), r.size === 0 && wr.delete(n)) : r.set(e, i);
			}
			ur.delete(f), s !== n && s.parentNode?.removeChild(s);
		};
	});
	return Er.set(u, d), u;
}
var Er = /* @__PURE__ */ new WeakMap();
function Dr(e, t) {
	let n = Er.get(e);
	return n ? (Er.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var Or = class {
	anchor;
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = !0;
	constructor(e, t = !0) {
		this.anchor = e, this.#i = t;
	}
	#a = (e) => {
		if (this.#e.has(e)) {
			var t = this.#e.get(e), n = this.#t.get(t);
			if (n) Ln(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
			}
			for (let [t, n] of this.#e) {
				if (this.#e.delete(t), t === e) break;
				let r = this.#n.get(n);
				r && (B(r.effect), this.#n.delete(n));
			}
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = document.createDocumentFragment();
						zn(r, t), t.append(an()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else B(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), Fn(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (B(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = A, r = ln();
		if (t && !this.#t.has(e) && !this.#n.has(e)) if (r) {
			var i = document.createDocumentFragment(), a = an();
			i.append(a), this.#n.set(e, {
				effect: z(() => t(a)),
				fragment: i
			});
		} else this.#t.set(e, z(() => t(this.anchor)));
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else w && (this.anchor = T), this.#a(n);
	}
};
function kr(e) {
	O === null && Se("onMount"), t && O.l !== null ? Ar(O).m.push(e) : bn(() => {
		let t = ar(e);
		if (typeof t == "function") return t;
	});
}
function Ar(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function jr(e, t, n = !1) {
	var r;
	w && (r = T, Re());
	var i = new Or(e), a = n ? se : 0;
	function o(e, t) {
		if (w) {
			var n = Ve(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Be();
				E(a), i.anchor = a, Le(!1), i.ensure(e, t), Le(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	kn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/css.js
function Mr(e, t) {
	Tn(() => {
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = un("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Nr = Symbol("is custom element"), Pr = Symbol("is html"), Fr = xe ? "link" : "LINK";
function Ir(e) {
	if (w) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Lr(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Lr(e, "checked", null), e.checked = r;
				}
			}
		};
		e[ye] = n, Ze(n), pn();
	}
}
function Lr(e, t, n, r) {
	var i = zr(e);
	w && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Fr) || i[t] !== (i[t] = n) && (t === "loading" && (e[me] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && Vr(e).includes(t) ? e[t] = n : e.setAttribute(t, n));
}
function Rr(e, t, n) {
	var r = H, i = G;
	let a = w;
	w && Le(!1), W(null), K(null);
	try {
		t !== "style" && (Br.has(e.getAttribute("is") || e.nodeName) || !customElements || customElements.get(e.getAttribute("is") || e.nodeName.toLowerCase()) ? Vr(e).includes(t) : n && typeof n == "object") ? e[t] = n : Lr(e, t, n == null ? n : String(n));
	} finally {
		W(r), K(i), a && Le(!0);
	}
}
function zr(e) {
	return e[he] ??= {
		[Nr]: e.nodeName.includes("-"),
		[Pr]: e.namespaceURI === a
	};
}
var Br = /* @__PURE__ */ new Map();
function Vr(e) {
	var t = e.getAttribute("is") || e.nodeName, n = Br.get(t);
	if (n) return n;
	Br.set(t, n = []);
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = p(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.push(o);
		i = g(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function Hr(t, n, r = n) {
	var i = /* @__PURE__ */ new WeakSet();
	hn(t, "input", async (e) => {
		var a = e ? t.defaultValue : t.value;
		if (a = Ur(t) ? Wr(a) : a, r(a), A !== null && i.add(A), await nr(), a !== (a = n())) {
			var o = t.selectionStart, s = t.selectionEnd, c = t.value.length;
			if (t.value = a ?? "", s !== null) {
				var l = t.value.length;
				o === s && s === c && l > c ? (t.selectionStart = l, t.selectionEnd = l) : (t.selectionStart = o, t.selectionEnd = Math.min(s, l));
			}
		}
	}), (w && t.defaultValue !== t.value || ar(n) == null && t.value) && (r(Ur(t) ? Wr(t.value) : t.value), A !== null && i.add(A)), Dn(() => {
		var r = n();
		if (t === document.activeElement) {
			var a = e ? ut : A;
			if (i.has(a)) return;
		}
		Ur(t) && r === Wr(t.value) || t.type === "date" && !r && !t.value || r !== t.value && (t.value = r ?? "");
	});
}
function Ur(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function Wr(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function Gr(e = !1) {
	let t = O, n = t.l.u;
	if (!n) return;
	let r = () => or(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ Ft(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Z(i);
	}
	n.b.length && Sn(() => {
		Kr(t, r), v(n.b);
	}), bn(() => {
		let e = ar(() => n.m.map(te));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && bn(() => {
		Kr(t, r), v(n.a);
	});
}
function Kr(e, t) {
	if (e.l.s) for (let t of e.l.s) Z(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function qr(e, n, r, i) {
	var a = !t || (r & 2) != 0, o = (r & 8) != 0, s = (r & 16) != 0, c = i, l = !0, u = void 0, d = () => s && a ? (u ??= /* @__PURE__ */ Ft(i), Z(u)) : (l && (l = !1, c = s ? ar(i) : i), c);
	let p;
	if (o) {
		var m = fe in e || pe in e;
		p = f(e, n)?.set ?? (m && n in e ? (t) => e[n] = t : void 0);
	}
	var h, g = !1;
	o ? [h, g] = st(() => e[n]) : h = e[n], h === void 0 && i !== void 0 && (h = d(), p && (a && ke(n), p(h)));
	var _ = a ? () => {
		var t = e[n];
		return t === void 0 ? d() : (l = !0, t);
	} : () => {
		var t = e[n];
		return t !== void 0 && (c = void 0), t === void 0 ? c : t;
	};
	if (a && !(r & 4)) return _;
	if (p) {
		var ee = e.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || ee || g) && p(t ? _() : e), e) : _();
		});
	}
	var te = !1, v = (r & 1 ? Ft : Rt)(() => (te = !1, _()));
	o && Z(v);
	var ne = G;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Z(v) : a && o ? Qt(e) : e;
			return F(v, n), te = !0, c !== void 0 && (c = n), e;
		}
		return V && te || ne.f & 16384 ? v.v : Z(v);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function Jr(e) {
	return new Yr(e);
}
var Yr = class {
	#e;
	#t;
	constructor(t) {
		var n = /* @__PURE__ */ new Map(), r = (e, t) => {
			var r = /* @__PURE__ */ P(t, !1, !1);
			return n.set(e, r), r;
		};
		let i = new Proxy({
			...t.props || {},
			$$events: {}
		}, {
			get(e, t) {
				return Z(n.get(t) ?? r(t, Reflect.get(e, t)));
			},
			has(e, t) {
				return t === pe ? !0 : (Z(n.get(t) ?? r(t, Reflect.get(e, t))), Reflect.has(e, t));
			},
			set(e, t, i) {
				return F(n.get(t) ?? r(t, i), i), Reflect.set(e, t, i);
			}
		});
		this.#t = (t.hydrate ? Cr : Sr)(t.component, {
			target: t.target,
			anchor: t.anchor,
			props: i,
			context: t.context,
			intro: t.intro ?? !1,
			recover: t.recover,
			transformError: t.transformError
		}), !e && (!t?.props?.$$host || t.sync === !1) && yt(), this.#e = i.$$events;
		for (let e of Object.keys(this.#t)) e === "$set" || e === "$destroy" || e === "$on" || d(this, e, {
			get() {
				return this.#t[e];
			},
			set(t) {
				this.#t[e] = t;
			},
			enumerable: !0
		});
		this.#t.$set = (e) => {
			Object.assign(i, e);
		}, this.#t.$destroy = () => {
			Dr(this.#t);
		};
	}
	$set(e) {
		this.#t.$set(e);
	}
	$on(e, t) {
		this.#e[e] = this.#e[e] || [];
		let n = (...e) => t.call(this, ...e);
		return this.#e[e].push(n), () => {
			this.#e[e] = this.#e[e].filter((e) => e !== n);
		};
	}
	$destroy() {
		this.#t.$destroy();
	}
}, Xr;
typeof HTMLElement == "function" && (Xr = class extends HTMLElement {
	$$ctor;
	$$s;
	$$c;
	$$cn = !1;
	$$d = {};
	$$r = !1;
	$$p_d = {};
	$$l = {};
	$$l_u = /* @__PURE__ */ new Map();
	$$me;
	$$shadowRoot = null;
	constructor(e, t, n) {
		super(), this.$$ctor = e, this.$$s = t, n && (this.$$shadowRoot = this.attachShadow(n));
	}
	addEventListener(e, t, n) {
		if (this.$$l[e] = this.$$l[e] || [], this.$$l[e].push(t), this.$$c) {
			let n = this.$$c.$on(e, t);
			this.$$l_u.set(t, n);
		}
		super.addEventListener(e, t, n);
	}
	removeEventListener(e, t, n) {
		if (super.removeEventListener(e, t, n), this.$$c) {
			let e = this.$$l_u.get(t);
			e && (e(), this.$$l_u.delete(t));
		}
	}
	async connectedCallback() {
		if (this.$$cn = !0, !this.$$c) {
			if (await Promise.resolve(), !this.$$cn || this.$$c) return;
			function e(e) {
				return (t) => {
					let n = un("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = Qr(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = Zr(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = Jr({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = Cn(() => {
				Dn(() => {
					this.$$r = !0;
					for (let e of u(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = Zr(e, this.$$d[e], this.$$p_d, "toAttribute");
						t == null ? this.removeAttribute(this.$$p_d[e].attribute || e) : this.setAttribute(this.$$p_d[e].attribute || e, t);
					}
					this.$$r = !1;
				});
			});
			for (let e in this.$$l) for (let t of this.$$l[e]) {
				let n = this.$$c.$on(e, t);
				this.$$l_u.set(t, n);
			}
			this.$$l = {};
		}
	}
	attributeChangedCallback(e, t, n) {
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = Zr(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
	}
	disconnectedCallback() {
		this.$$cn = !1, Promise.resolve().then(() => {
			!this.$$cn && this.$$c && (this.$$c.$destroy(), this.$$me(), this.$$c = void 0);
		});
	}
	$$g_p(e) {
		return u(this.$$p_d).find((t) => this.$$p_d[t].attribute === e || !this.$$p_d[t].attribute && t.toLowerCase() === e) || e;
	}
});
function Zr(e, t, n, r) {
	let i = n[e]?.type;
	if (t = i === "Boolean" && typeof t != "boolean" ? t != null : t, !r || !n[e]) return t;
	if (r === "toAttribute") switch (i) {
		case "Object":
		case "Array": return t == null ? null : JSON.stringify(t);
		case "Boolean": return t ? "" : null;
		case "Number": return t ?? null;
		default: return t;
	}
	else switch (i) {
		case "Object":
		case "Array": return t && JSON.parse(t);
		case "Boolean": return t;
		case "Number": return t == null ? t : +t;
		default: return t;
	}
}
function Qr(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function $r(e, t, n, r, i, a) {
	let o = class extends Xr {
		constructor() {
			super(e, n, i), this.$$p_d = t;
		}
		static get observedAttributes() {
			return u(t).map((e) => (t[e].attribute || e).toLowerCase());
		}
	};
	return u(t).forEach((e) => {
		d(o.prototype, e, {
			get() {
				return this.$$c && e in this.$$c ? this.$$c[e] : this.$$d[e];
			},
			set(n) {
				n = Zr(e, n, t), this.$$d[e] = n;
				var r = this.$$c;
				r && (f(r, e)?.get ? r[e] = n : r.$set({ [e]: n }));
			}
		});
	}), r.forEach((e) => {
		d(o.prototype, e, { get() {
			return this.$$c?.[e];
		} });
	}), a && (o = a(o)), e.element = o, o;
}
//#endregion
//#region JellyfinCard.svelte
var ei = /* @__PURE__ */ Q("<span class=\"status-badge active svelte-1uhbaav\">● Active</span>"), ti = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-1uhbaav\">✓ Authenticated</span>"), ni = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-1uhbaav\">● Connected</span>"), ri = /* @__PURE__ */ Q("<span class=\"status-badge warning svelte-1uhbaav\">⚠ Disconnected</span>"), ii = /* @__PURE__ */ Q("<div class=\"loading-state svelte-1uhbaav\">Loading...</div>"), ai = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-1uhbaav\"> </button>"), oi = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-1uhbaav\"> </button>"), si = /* @__PURE__ */ Q("<div class=\"settings-section svelte-1uhbaav\"><h3 class=\"section-title svelte-1uhbaav\">Server Configuration</h3> <div class=\"form-grid svelte-1uhbaav\"><label class=\"form-field svelte-1uhbaav\"><span class=\"field-label svelte-1uhbaav\">Server URL</span> <input type=\"text\" placeholder=\"http://192.168.1.100:8096\" class=\"input-field svelte-1uhbaav\"/> <span class=\"helper-text svelte-1uhbaav\">Enter your Jellyfin server URL (include port, typically :8096)</span></label> <label class=\"form-field svelte-1uhbaav\"><span class=\"field-label svelte-1uhbaav\">Username</span> <input type=\"text\" placeholder=\"Enter username\" class=\"input-field svelte-1uhbaav\"/></label> <label class=\"form-field svelte-1uhbaav\"><span class=\"field-label svelte-1uhbaav\">Password</span> <div class=\"password-wrapper svelte-1uhbaav\"><input class=\"input-field svelte-1uhbaav\"/> <button type=\"button\" class=\"toggle-visibility svelte-1uhbaav\"> </button></div></label> <div class=\"path-mappings svelte-1uhbaav\"><echosync-path-mapping-editor></echosync-path-mapping-editor></div> <div class=\"actions-row svelte-1uhbaav\"><button class=\"btn-primary svelte-1uhbaav\"> </button> <!> <!></div></div></div>", 2), ci = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-1uhbaav\"><div class=\"card-header svelte-1uhbaav\"><div class=\"header-left svelte-1uhbaav\"><h2 class=\"card-title svelte-1uhbaav\">Jellyfin</h2> <div class=\"badges svelte-1uhbaav\"><!> <!> <!></div></div> <button class=\"btn-ghost svelte-1uhbaav\"> </button></div> <!></section>"), li = {
	hash: "svelte-1uhbaav",
	code: ".plugin-card.svelte-1uhbaav {background:var(--bg-surface);border:1px solid var(--border-subtle);border-radius:var(--radius, 16px);padding:28px;color:var(--text-primary);font-family:'Inter', sans-serif;box-shadow:0 4px 24px rgba(0, 0, 0, 0.2);}.card-header.svelte-1uhbaav {display:flex;justify-content:space-between;align-items:center;margin-bottom:28px;padding-bottom:20px;border-bottom:1px solid var(--border-subtle);}.header-left.svelte-1uhbaav {display:flex;align-items:center;gap:16px;}.card-title.svelte-1uhbaav {margin:0;font-size:22px;font-weight:800;letter-spacing:-0.02em;background:linear-gradient(135deg, #fff 0%, #a5b4fc 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}.badges.svelte-1uhbaav {display:flex;gap:8px;}.status-badge.svelte-1uhbaav {font-size:10px;padding:3px 10px;border-radius:6px;font-weight:800;text-transform:uppercase;letter-spacing:0.03em;}.status-badge.active.svelte-1uhbaav {background:rgba(20, 184, 166, 0.1);color:var(--color-primary);border:1px solid rgba(20, 184, 166, 0.2);}.status-badge.success.svelte-1uhbaav {background:rgba(16, 185, 129, 0.1);color:#10b981;border:1px solid rgba(16, 185, 129, 0.2);}.status-badge.warning.svelte-1uhbaav {background:rgba(245, 158, 11, 0.1);color:#f59e0b;border:1px solid rgba(245, 158, 11, 0.2);}.btn-ghost.svelte-1uhbaav {padding:10px 18px;background:rgba(255, 255, 255, 0.05);border:1px solid var(--border-subtle);color:var(--text-primary);border-radius:10px;font-size:13px;font-weight:600;cursor:pointer;transition:all 0.2s ease;}.btn-ghost.svelte-1uhbaav:hover {background:rgba(255, 255, 255, 0.1);border-color:rgba(255, 255, 255, 0.2);transform:translateY(-1px);}.btn-primary.svelte-1uhbaav {padding:12px 28px;background:var(--color-primary);color:#000;border:none;border-radius:12px;font-weight:700;font-size:14px;cursor:pointer;transition:all 0.3s cubic-bezier(0.4, 0, 0.2, 1);box-shadow:0 4px 12px rgba(20, 184, 166, 0.2);}.btn-primary.svelte-1uhbaav:hover:not(:disabled) {filter:brightness(1.1);transform:translateY(-2px);box-shadow:0 6px 20px rgba(20, 184, 166, 0.3);}.btn-primary.svelte-1uhbaav:disabled {opacity:0.4;cursor:not-allowed;}.loading-state.svelte-1uhbaav {display:flex;flex-direction:column;align-items:center;gap:20px;padding:60px;color:var(--text-muted);}.settings-section.svelte-1uhbaav {margin-top:24px;}.section-title.svelte-1uhbaav {margin:0 0 20px 0;font-size:14px;font-weight:700;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.05em;}.form-grid.svelte-1uhbaav {display:grid;grid-template-columns:1fr;gap:20px;}\n\n  @media (min-width: 640px) {.form-grid.svelte-1uhbaav {grid-template-columns:1fr 1fr;}.actions-row.svelte-1uhbaav, .path-mappings.svelte-1uhbaav {grid-column:span 2;}\n  }.form-field.svelte-1uhbaav {display:flex;flex-direction:column;gap:10px;}.field-label.svelte-1uhbaav {font-size:12px;font-weight:600;color:var(--text-secondary);opacity:0.8;}.input-field.svelte-1uhbaav {width:100%;padding:14px 18px;background:var(--bg-input, #0f172a);border:1px solid var(--border-subtle);border-radius:12px;color:var(--text-primary);font-size:14px;transition:all 0.25s cubic-bezier(0.4, 0, 0.2, 1);}.input-field.svelte-1uhbaav:focus {outline:none;border-color:var(--color-primary);box-shadow:0 0 0 4px rgba(20, 184, 166, 0.15);background:rgba(255, 255, 255, 0.03);}.password-wrapper.svelte-1uhbaav {position:relative;display:flex;align-items:center;}.toggle-visibility.svelte-1uhbaav {position:absolute;right:14px;background:none;border:none;cursor:pointer;opacity:0.6;color:var(--text-primary);font-size:18px;padding:0;display:flex;align-items:center;justify-content:center;}.toggle-visibility.svelte-1uhbaav:hover {opacity:1;}.helper-text.svelte-1uhbaav {font-size:11px;color:var(--text-muted);margin-top:6px;font-style:italic;}.path-mappings.svelte-1uhbaav {padding:24px 0;border-top:1px solid var(--border-subtle);margin-top:12px;}.actions-row.svelte-1uhbaav {display:flex;gap:16px;flex-wrap:wrap;margin-top:12px;}"
};
function ui(e, t) {
	Ke(t, !1), Mr(e, li);
	let n = qr(t, "apiBase", 12, ""), r = /* @__PURE__ */ P(""), i = /* @__PURE__ */ P(""), a = /* @__PURE__ */ P(""), o = /* @__PURE__ */ P([]), s = /* @__PURE__ */ P(!1), c = /* @__PURE__ */ P(!1), l = /* @__PURE__ */ P(!0), u = /* @__PURE__ */ P(!1), d = /* @__PURE__ */ P(!1), f = /* @__PURE__ */ P(!1), p = /* @__PURE__ */ P(!1), m = /* @__PURE__ */ P(!1), h = /* @__PURE__ */ P(!1);
	kr(async () => {
		await _(), F(l, !1);
	});
	async function g() {
		try {
			F(h, !0), await fetch(`${n()}/jellyfin/activate`, { method: "POST" }), await _();
		} catch (e) {
			console.error("Failed to activate server:", e);
		} finally {
			F(h, !1);
		}
	}
	async function _() {
		try {
			let e = await (await fetch(`${n()}/jellyfin/settings`)).json();
			e?.settings && (F(r, e.settings.base_url || ""), F(i, e.settings.username || ""), F(o, e.settings.path_mappings || []), F(s, e.settings.has_password || !1), F(c, e.settings.connected || !1), F(m, e.settings.is_active || !1), F(a, ""));
		} catch (e) {
			console.error("Failed to load Jellyfin settings:", e);
		}
	}
	async function ee() {
		if (!Z(r).trim()) {
			console.error("Server URL is required");
			return;
		}
		if (!Z(i).trim() || !Z(s) && !Z(a).trim()) {
			console.error("Username and password are required");
			return;
		}
		try {
			F(u, !0), await fetch(`${n()}/jellyfin/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					base_url: Z(r),
					username: Z(i),
					password: Z(a),
					path_mappings: Z(o)
				})
			}), await _();
		} catch (e) {
			console.error("Failed to save Jellyfin settings:", e);
		} finally {
			F(u, !1);
		}
	}
	async function te() {
		try {
			F(d, !0), (await (await fetch(`${n()}/jellyfin/test-connection`, { method: "POST" })).json())?.connected && await _();
		} catch (e) {
			console.error("Connection test failed:", e);
		} finally {
			F(d, !1);
		}
	}
	var v = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), yt();
		}
	};
	Gr();
	var ne = ci(), y = I(ne), b = I(y), x = L(I(b), 2), re = I(x), ie = (e) => {
		$(e, ei());
	};
	jr(re, (e) => {
		Z(m) && e(ie);
	});
	var ae = L(re, 2), oe = (e) => {
		$(e, ti());
	};
	jr(ae, (e) => {
		Z(s) && e(oe);
	});
	var se = L(ae, 2), S = (e) => {
		$(e, ni());
	}, ce = (e) => {
		$(e, ri());
	};
	jr(se, (e) => {
		Z(c) ? e(S) : Z(s) && e(ce, 1);
	}), D(x), D(b);
	var C = L(b, 2), le = I(C, !0);
	D(C), D(y);
	var ue = L(y, 2), de = (e) => {
		$(e, ii());
	}, fe = (e) => {
		var t = si(), n = L(I(t), 2), c = I(n), l = L(I(c), 2);
		Ir(l), ze(2), D(c);
		var f = L(c, 2), _ = L(I(f), 2);
		Ir(_), D(f);
		var v = L(f, 2), ne = L(I(v), 2), y = I(ne);
		Ir(y);
		var b = L(y, 2), x = I(b, !0);
		D(b), D(ne), D(v);
		var re = L(v, 2), ie = I(re);
		On(() => Rr(ie, "mappings", (Z(o), ar(() => JSON.stringify(Z(o)))))), D(re);
		var ae = L(re, 2), oe = I(ae), se = I(oe, !0);
		D(oe);
		var S = L(oe, 2), ce = (e) => {
			var t = ai(), n = I(t, !0);
			D(t), On(() => {
				t.disabled = Z(d), xr(n, Z(d) ? "Testing..." : "Test Connection");
			}), fr("click", t, te), $(e, t);
		};
		jr(S, (e) => {
			Z(s) && e(ce);
		});
		var C = L(S, 2), le = (e) => {
			var t = oi(), n = I(t, !0);
			D(t), On(() => {
				t.disabled = Z(h), xr(n, Z(h) ? "Activating..." : "Activate Server");
			}), fr("click", t, g), $(e, t);
		};
		jr(C, (e) => {
			Z(m) || e(le);
		}), D(ae), D(n), D(t), On(() => {
			Lr(y, "type", Z(p) ? "text" : "password"), Lr(y, "placeholder", Z(s) ? "••••••••" : "Enter password"), xr(x, Z(p) ? "🙈" : "👁️"), oe.disabled = Z(u), xr(se, Z(u) ? "Saving..." : "Save Settings");
		}), Hr(l, () => Z(r), (e) => F(r, e)), Hr(_, () => Z(i), (e) => F(i, e)), Hr(y, () => Z(a), (e) => F(a, e)), fr("click", b, () => F(p, !Z(p))), fr("es-path-update", ie, (e) => F(o, e.detail)), fr("click", oe, ee), $(e, t);
	};
	return jr(ue, (e) => {
		Z(l) ? e(de) : Z(f) || e(fe, 1);
	}), D(ne), On(() => xr(le, Z(f) ? "Expand" : "Collapse")), fr("click", C, () => F(f, !Z(f))), $(e, ne), qe(v);
}
customElements.define("jellyfin-dashboard-card", $r(ui, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
export { ui as default };
