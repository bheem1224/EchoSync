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
var r = {}, i = Symbol(), a = "http://www.w3.org/1999/xhtml", o = Array.isArray, s = Array.prototype.indexOf, c = Array.prototype.includes, l = Array.from, u = Object.keys, d = Object.defineProperty, f = Object.getOwnPropertyDescriptor, p = Object.getOwnPropertyDescriptors, m = Object.prototype, h = Array.prototype, g = Object.getPrototypeOf, _ = Object.isExtensible, ee = () => {};
function te(e) {
	return e();
}
function ne(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function re() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var v = 1024, y = 2048, b = 4096, ie = 8192, ae = 16384, oe = 32768, se = 1 << 25, ce = 65536, x = 1 << 19, le = 1 << 20, ue = 65536, de = 1 << 21, fe = 1 << 22, pe = 1 << 23, me = Symbol("$state"), he = Symbol("legacy props"), ge = Symbol(""), S = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), _e = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function ve(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
//#endregion
//#region node_modules/svelte/src/internal/client/errors.js
function ye() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function be(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function xe() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function Se(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function Ce() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function we() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function Te(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function Ee() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function De() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Oe() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function ke() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
function Ae() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function je(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function Me() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/hydration.js
var C = !1;
function Ne(e) {
	C = e;
}
var w;
function T(e) {
	if (e === null) throw je(), r;
	return w = e;
}
function Pe() {
	return T(/* @__PURE__ */ Qt(w));
}
function E(e) {
	if (C) {
		if (/* @__PURE__ */ Qt(w) !== null) throw je(), r;
		w = e;
	}
}
function Fe(e = 1) {
	if (C) {
		for (var t = e, n = w; t--;) n = /* @__PURE__ */ Qt(n);
		w = n;
	}
}
function Ie(e = !0) {
	for (var t = 0, n = w;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ Qt(n);
		e && n.remove(), n = i;
	}
}
function Le(e) {
	if (!e || e.nodeType !== 8) throw je(), r;
	return e.data;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/equality.js
function Re(e) {
	return e === this.v;
}
function ze(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function Be(e) {
	return !ze(e, this.v);
}
//#endregion
//#region node_modules/svelte/src/internal/client/context.js
var D = null;
function Ve(e) {
	D = e;
}
function He(e, n = !1, r) {
	D = {
		p: D,
		i: !1,
		c: null,
		e: null,
		s: e,
		x: null,
		r: K,
		l: t && !n ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function Ue(e) {
	var t = D, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) pn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, D = t.p, e ?? {};
}
function We() {
	return !t || D !== null && D.l === null;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/task.js
var Ge = [];
function Ke() {
	var e = Ge;
	Ge = [], ne(e);
}
function O(e) {
	if (Ge.length === 0 && !at) {
		var t = Ge;
		queueMicrotask(() => {
			t === Ge && Ke();
		});
	}
	Ge.push(e);
}
function qe() {
	for (; Ge.length > 0;) Ke();
}
function Je(e) {
	var t = K;
	if (t === null) return U.f |= pe, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	Ye(e, t);
}
function Ye(e, t) {
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
var Xe = ~(y | b | v);
function k(e, t) {
	e.f = e.f & Xe | t;
}
function Ze(e) {
	e.f & 512 || e.deps === null ? k(e, v) : k(e, b);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/utils.js
function Qe(e) {
	if (e !== null) for (let t of e) !(t.f & 2) || !(t.f & 65536) || (t.f ^= ue, Qe(t.deps));
}
function $e(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), Qe(e.deps), k(e, v);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/store.js
var et = !1, tt = !1;
function nt(e) {
	var t = tt;
	try {
		return tt = !1, [e(), tt];
	} finally {
		tt = t;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/batch.js
var A = /* @__PURE__ */ new Set(), j = null, rt = null, M = null, it = null, at = !1, ot = !1, st = null, ct = null, lt = 0, ut = 1, dt = class t {
	id = ut++;
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	#e = /* @__PURE__ */ new Set();
	#t = /* @__PURE__ */ new Set();
	#n = /* @__PURE__ */ new Set();
	#r = /* @__PURE__ */ new Map();
	#i = /* @__PURE__ */ new Map();
	#a = null;
	#o = [];
	#s = [];
	#c = /* @__PURE__ */ new Set();
	#l = /* @__PURE__ */ new Set();
	#u = /* @__PURE__ */ new Map();
	#d = /* @__PURE__ */ new Set();
	is_fork = !1;
	#f = !1;
	#p = /* @__PURE__ */ new Set();
	#m() {
		return this.is_fork || this.#i.size > 0;
	}
	#h() {
		for (let n of this.#p) for (let r of n.#i.keys()) {
			for (var e = !1, t = r; t.parent !== null;) {
				if (this.#u.has(t)) {
					e = !0;
					break;
				}
				t = t.parent;
			}
			if (!e) return !0;
		}
		return !1;
	}
	skip_effect(e) {
		this.#u.has(e) || this.#u.set(e, {
			d: [],
			m: []
		}), this.#d.delete(e);
	}
	unskip_effect(e, t = (e) => this.schedule(e)) {
		var n = this.#u.get(e);
		if (n) {
			this.#u.delete(e);
			for (var r of n.d) k(r, y), t(r);
			for (r of n.m) k(r, b), t(r);
		}
		this.#d.add(e);
	}
	#g() {
		if (lt++ > 1e3 && (A.delete(this), pt()), !this.#m()) {
			for (let e of this.#c) this.#l.delete(e), k(e, y), this.schedule(e);
			for (let e of this.#l) k(e, b), this.schedule(e);
		}
		let n = this.#o;
		this.#o = [], this.apply();
		var r = st = [], i = [], a = ct = [];
		for (let e of n) try {
			this.#_(e, r, i);
		} catch (t) {
			throw yt(e), t;
		}
		if (j = null, a.length > 0) {
			var o = t.ensure();
			for (let e of a) o.schedule(e);
		}
		if (st = null, ct = null, this.#m() || this.#h()) {
			this.#v(i), this.#v(r);
			for (let [e, t] of this.#u) vt(e, t);
		} else {
			this.#r.size === 0 && A.delete(this), this.#c.clear(), this.#l.clear();
			for (let e of this.#e) e(this);
			this.#e.clear(), rt = this, mt(i), mt(r), rt = null, this.#a?.resolve();
		}
		var s = j;
		if (this.#o.length > 0) {
			let e = s ??= this;
			e.#o.push(...this.#o.filter((t) => !e.#o.includes(t)));
		}
		s !== null && (A.add(s), s.#g()), e && !A.has(this) && this.#y();
	}
	#_(t, n, r) {
		t.f ^= v;
		for (var i = t.first; i !== null;) {
			var a = i.f, o = (a & 96) != 0;
			if (!(o && a & 1024 || a & 8192 || this.#u.has(i)) && i.fn !== null) {
				o ? i.f ^= v : a & 4 ? n.push(i) : e && a & 16777224 ? r.push(i) : Vn(i) && (a & 16 && this.#l.add(i), Kn(i));
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
	#v(e) {
		for (var t = 0; t < e.length; t += 1) $e(e[t], this.#c, this.#l);
	}
	capture(e, t, n = !1) {
		e.v !== i && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), M?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		j = this;
	}
	deactivate() {
		j = null, M = null;
	}
	flush() {
		try {
			ot = !0, j = this, this.#g();
		} finally {
			lt = 0, it = null, st = null, ct = null, ot = !1, j = null, M = null, Lt.clear();
		}
	}
	discard() {
		for (let e of this.#t) e(this);
		this.#t.clear(), this.#n.clear(), A.delete(this);
	}
	register_created_effect(e) {
		this.#s.push(e);
	}
	#y() {
		for (let l of A) {
			var e = l.id < this.id, t = [];
			for (let [r, [i, a]] of this.current) {
				if (l.current.has(r)) {
					var n = l.current.get(r)[0];
					if (e && i !== n) l.current.set(r, [i, a]);
					else continue;
				}
				t.push(r);
			}
			var r = [...l.current.keys()].filter((e) => !this.current.has(e));
			if (r.length === 0) e && l.discard();
			else if (t.length > 0) {
				if (e) for (let e of this.#d) l.unskip_effect(e, (e) => {
					e.f & 4194320 ? l.schedule(e) : l.#v([e]);
				});
				l.activate();
				var i = /* @__PURE__ */ new Set(), a = /* @__PURE__ */ new Map();
				for (var o of t) ht(o, r, i, a);
				a = /* @__PURE__ */ new Map();
				var s = [...l.current.keys()].filter((e) => this.current.has(e) ? this.current.get(e)[0] !== e : !0);
				for (let e of this.#s) !(e.f & 155648) && gt(e, s, a) && (e.f & 4194320 ? (k(e, y), l.schedule(e)) : l.#c.add(e));
				if (l.#o.length > 0) {
					l.apply();
					for (var c of l.#o) l.#_(c, [], []);
					l.#o = [];
				}
				l.deactivate();
			}
		}
		for (let e of A) e.#p.has(this) && (e.#p.delete(this), e.#p.size === 0 && !e.#m() && (e.activate(), e.#g()));
	}
	increment(e, t) {
		let n = this.#r.get(t) ?? 0;
		if (this.#r.set(t, n + 1), e) {
			let e = this.#i.get(t) ?? 0;
			this.#i.set(t, e + 1);
		}
	}
	decrement(e, t, n) {
		let r = this.#r.get(t) ?? 0;
		if (r === 1 ? this.#r.delete(t) : this.#r.set(t, r - 1), e) {
			let e = this.#i.get(t) ?? 0;
			e === 1 ? this.#i.delete(t) : this.#i.set(t, e - 1);
		}
		this.#f || n || (this.#f = !0, O(() => {
			this.#f = !1, this.flush();
		}));
	}
	transfer_effects(e, t) {
		for (let t of e) this.#c.add(t);
		for (let e of t) this.#l.add(e);
		e.clear(), t.clear();
	}
	oncommit(e) {
		this.#e.add(e);
	}
	ondiscard(e) {
		this.#t.add(e);
	}
	on_fork_commit(e) {
		this.#n.add(e);
	}
	run_fork_commit_callbacks() {
		for (let e of this.#n) e(this);
		this.#n.clear();
	}
	settled() {
		return (this.#a ??= re()).promise;
	}
	static ensure() {
		if (j === null) {
			let e = j = new t();
			ot || (A.add(j), at || O(() => {
				j === e && e.flush();
			}));
		}
		return j;
	}
	apply() {
		if (!e || !this.is_fork && A.size === 1) {
			M = null;
			return;
		}
		M = /* @__PURE__ */ new Map();
		for (let [e, [t]] of this.current) M.set(e, t);
		for (let e of A) if (!(e === this || e.is_fork)) {
			var t = !1, n = !1;
			if (e.id < this.id) for (let [r, [, i]] of e.current) i || (t ||= this.current.has(r), n ||= !this.current.has(r));
			if (t && n) this.#p.add(e);
			else for (let [t, n] of e.previous) M.has(t) || M.set(t, n);
		}
	}
	schedule(t) {
		if (it = t, t.b?.is_pending && t.f & 16777228 && !(t.f & 32768)) {
			t.b.defer_effect(t);
			return;
		}
		for (var n = t; n.parent !== null;) {
			n = n.parent;
			var r = n.f;
			if (st !== null && n === K && (e || (U === null || !(U.f & 2)) && !et)) return;
			if (r & 96) {
				if (!(r & 1024)) return;
				n.f ^= v;
			}
		}
		this.#o.push(n);
	}
};
function ft(e) {
	var t = at;
	at = !0;
	try {
		var n;
		for (e && (j !== null && !j.is_fork && j.flush(), n = e());;) {
			if (qe(), j === null) return n;
			j.flush();
		}
	} finally {
		at = t;
	}
}
function pt() {
	try {
		Ce();
	} catch (e) {
		Ye(e, it);
	}
}
var N = null;
function mt(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && Vn(r) && (N = /* @__PURE__ */ new Set(), Kn(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && Tn(r), N?.size > 0)) {
				Lt.clear();
				for (let e of N) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) N.has(n) && (N.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || Kn(n);
					}
				}
				N.clear();
			}
		}
		N = null;
	}
}
function ht(e, t, n, r) {
	if (!n.has(e) && (n.add(e), e.reactions !== null)) for (let i of e.reactions) {
		let e = i.f;
		e & 2 ? ht(i, t, n, r) : e & 4194320 && !(e & 2048) && gt(i, t, r) && (k(i, y), _t(i));
	}
}
function gt(e, t, n) {
	let r = n.get(e);
	if (r !== void 0) return r;
	if (e.deps !== null) for (let r of e.deps) {
		if (c.call(t, r)) return !0;
		if (r.f & 2 && gt(r, t, n)) return n.set(r, !0), !0;
	}
	return n.set(e, !1), !1;
}
function _t(e) {
	j.schedule(e);
}
function vt(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), k(e, v);
		for (var n = e.first; n !== null;) vt(n, t), n = n.next;
	}
}
function yt(e) {
	k(e, v);
	for (var t = e.first; t !== null;) yt(t), t = t.next;
}
//#endregion
//#region node_modules/svelte/src/reactivity/create-subscriber.js
function bt(e) {
	let t = 0, n = zt(0), r;
	return () => {
		un() && (Q(n), vn(() => (t === 0 && (r = Xn(() => e(() => Ht(n)))), t += 1, () => {
			O(() => {
				--t, t === 0 && (r?.(), r = void 0, Ht(n));
			});
		})));
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var xt = ce | x;
function St(e, t, n, r) {
	new Ct(e, t, n, r);
}
var Ct = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = C ? w : null;
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
	#h = bt(() => (this.#m = zt(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = K;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = K.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = bn(() => {
			if (C) {
				let e = this.#t;
				Pe();
				let t = e.data === "[!";
				if (e.data.startsWith("[?")) {
					let t = JSON.parse(e.data.slice(2));
					this.#_(t);
				} else t ? this.#v() : this.#g();
			} else this.#y();
		}, xt), C && (this.#e = w);
	}
	#g() {
		try {
			this.#a = B(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed;
		t && (this.#s = B(() => {
			t(this.#e, () => e, () => () => {});
		}));
	}
	#v() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = B(() => e(this.#e)), O(() => {
			var e = this.#c = document.createDocumentFragment(), t = Xt();
			e.append(t), this.#a = this.#x(() => B(() => this.#r(t))), this.#u === 0 && (this.#e.before(e), this.#c = null, En(this.#o, () => {
				this.#o = null;
			}), this.#b(j));
		}));
	}
	#y() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = B(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				An(this.#a, e);
				let t = this.#n.pending;
				this.#o = B(() => t(this.#e));
			} else this.#b(j);
		} catch (e) {
			this.error(e);
		}
	}
	#b(e) {
		this.is_pending = !1, e.transfer_effects(this.#f, this.#p);
	}
	defer_effect(e) {
		$e(e, this.#f, this.#p);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#x(e) {
		var t = K, n = U, r = D;
		q(this.#i), G(this.#i), Ve(this.#i.ctx);
		try {
			return dt.ensure(), e();
		} catch (e) {
			return Je(e), null;
		} finally {
			q(t), G(n), Ve(r);
		}
	}
	#S(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#S(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#b(t), this.#o && En(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#S(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, O(() => {
			this.#d = !1, this.#m && Bt(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), Q(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		j?.is_fork ? (this.#a && j.skip_effect(this.#a), this.#o && j.skip_effect(this.#o), this.#s && j.skip_effect(this.#s), j.on_fork_commit(() => {
			this.#C(e);
		})) : this.#C(e);
	}
	#C(e) {
		this.#a &&= (V(this.#a), null), this.#o &&= (V(this.#o), null), this.#s &&= (V(this.#s), null), C && (T(this.#t), Fe(), T(Ie()));
		var t = this.#n.onerror;
		let n = this.#n.failed;
		var r = !1, i = !1;
		let a = () => {
			if (r) {
				Me();
				return;
			}
			r = !0, i && ke(), this.#s !== null && En(this.#s, () => {
				this.#s = null;
			}), this.#x(() => {
				this.#y();
			});
		}, o = (e) => {
			try {
				i = !0, t?.(e, a), i = !1;
			} catch (e) {
				Ye(e, this.#i && this.#i.parent);
			}
			n && (this.#s = this.#x(() => {
				try {
					return B(() => {
						var t = K;
						t.b = this, t.f |= 128, n(this.#e, () => e, () => a);
					});
				} catch (e) {
					return Ye(e, this.#i.parent), null;
				}
			}));
		};
		O(() => {
			var t;
			try {
				t = this.transform_error(e);
			} catch (e) {
				Ye(e, this.#i && this.#i.parent);
				return;
			}
			typeof t == "object" && t && typeof t.then == "function" ? t.then(o, (e) => Ye(e, this.#i && this.#i.parent)) : o(t);
		});
	}
};
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/async.js
function wt(e, t, n, r) {
	let i = We() ? Ot : At;
	var a = e.filter((e) => !e.settled);
	if (n.length === 0 && a.length === 0) {
		r(t.map(i));
		return;
	}
	var o = K, s = Tt(), c = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function l(e) {
		s();
		try {
			r(e);
		} catch (e) {
			o.f & 16384 || Ye(e, o);
		}
		Et();
	}
	if (n.length === 0) {
		c.then(() => l(t.map(i)));
		return;
	}
	var u = Dt();
	function d() {
		Promise.all(n.map((e) => /* @__PURE__ */ kt(e))).then((e) => l([...t.map(i), ...e])).catch((e) => Ye(e, o)).finally(() => u());
	}
	c ? c.then(() => {
		s(), d(), Et();
	}) : d();
}
function Tt() {
	var e = K, t = U, n = D, r = j;
	return function(i = !0) {
		q(e), G(t), Ve(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function Et(e = !0) {
	q(null), G(null), Ve(null), e && j?.deactivate();
}
function Dt() {
	var e = K, t = e.b, n = j, r = t.is_rendered();
	return t.update_pending_count(1, n), n.increment(r, e), (i = !1) => {
		t.update_pending_count(-1, n), n.decrement(r, e, i);
	};
}
/* @__NO_SIDE_EFFECTS__ */
function Ot(e) {
	var t = 2 | y;
	return K !== null && (K.f |= x), {
		ctx: D,
		deps: null,
		effects: null,
		equals: Re,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: i,
		wv: 0,
		parent: K,
		ac: null
	};
}
/* @__NO_SIDE_EFFECTS__ */
function kt(e, t, n) {
	let r = K;
	r === null && ye();
	var a = void 0, o = zt(i), s = !U, c = /* @__PURE__ */ new Map();
	return _n(() => {
		var t = K, n = re();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, n.reject).finally(Et);
		} catch (e) {
			n.reject(e), Et();
		}
		var i = j;
		if (s) {
			if (t.f & 32768) var l = Dt();
			if (r.b.is_rendered()) c.get(i)?.reject(S), c.delete(i);
			else {
				for (let e of c.values()) e.reject(S);
				c.clear();
			}
			c.set(i, n);
		}
		let u = (e, n = void 0) => {
			if (l && l(n === S), !(n === S || t.f & 16384)) {
				if (i.activate(), n) o.f |= pe, Bt(o, n);
				else {
					o.f & 8388608 && (o.f ^= pe), Bt(o, e);
					for (let [e, t] of c) {
						if (c.delete(e), e === i) break;
						t.reject(S);
					}
				}
				i.deactivate();
			}
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), dn(() => {
		for (let e of c.values()) e.reject(S);
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
function At(e) {
	let t = /* @__PURE__ */ Ot(e);
	return t.equals = Be, t;
}
function jt(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) V(t[n]);
	}
}
function Mt(e) {
	var t, n = K, r = e.parent;
	if (!H && r !== null && r.f & 24576) return Ae(), e.v;
	q(r);
	try {
		e.f &= ~ue, jt(e), t = Un(e);
	} finally {
		q(n);
	}
	return t;
}
function Nt(e) {
	var t = Mt(e);
	if (!e.equals(t) && (e.wv = Bn(), (!j?.is_fork || e.deps === null) && (j === null ? e.v = t : j.capture(e, t, !0), e.deps === null))) {
		k(e, v);
		return;
	}
	H || (M === null ? Ze(e) : (un() || j?.is_fork) && M.set(e, t));
}
function Pt(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac?.abort(S), t.teardown = ee, t.ac = null, Gn(t, 0), Sn(t));
}
function Ft(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && Kn(t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/sources.js
var It = /* @__PURE__ */ new Set(), Lt = /* @__PURE__ */ new Map(), Rt = !1;
function zt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: Re,
		rv: 0,
		wv: 0
	};
}
/* @__NO_SIDE_EFFECTS__ */
function P(e, t) {
	let n = zt(e, t);
	return Pn(n), n;
}
/* @__NO_SIDE_EFFECTS__ */
function F(e, n = !1, r = !0) {
	let i = zt(e);
	return n || (i.equals = Be), t && r && D !== null && D.l !== null && (D.l.s ??= []).push(i), i;
}
function I(e, t, n = !1) {
	return U !== null && (!W || U.f & 131072) && We() && U.f & 4325394 && (J === null || !c.call(J, e)) && Oe(), Bt(e, n ? Wt(t) : t, ct);
}
function Bt(e, t, n = null) {
	if (!e.equals(t)) {
		Lt.set(e, H ? t : e.v);
		var r = dt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && Mt(t), M === null && Ze(t);
		}
		e.wv = Bn(), Ut(e, y, n), We() && K !== null && K.f & 1024 && !(K.f & 96) && (Z === null ? Fn([e]) : Z.push(e)), !r.is_fork && It.size > 0 && !Rt && Vt();
	}
	return t;
}
function Vt() {
	Rt = !1;
	for (let e of It) e.f & 1024 && k(e, b), Vn(e) && Kn(e);
	It.clear();
}
function Ht(e) {
	I(e, e.v + 1);
}
function Ut(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = We(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (!(!i && s === K)) {
			var l = (c & y) === 0;
			if (l && k(s, t), c & 2) {
				var u = s;
				M?.delete(u), c & 65536 || (c & 512 && (K === null || !(K.f & 2097152)) && (s.f |= ue), Ut(u, b, n));
			} else if (l) {
				var d = s;
				c & 16 && N !== null && N.add(d), n === null ? _t(d) : n.push(d);
			}
		}
	}
}
function Wt(e) {
	if (typeof e != "object" || !e || me in e) return e;
	let t = g(e);
	if (t !== m && t !== h) return e;
	var n = /* @__PURE__ */ new Map(), r = o(e), a = /* @__PURE__ */ P(0), s = null, c = Rn, l = (e) => {
		if (Rn === c) return e();
		var t = U, n = Rn;
		G(null), zn(c);
		var r = e();
		return G(t), zn(n), r;
	};
	return r && n.set("length", /* @__PURE__ */ P(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && Ee();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ P(r.value, s);
				return n.set(t, e), e;
			}) : I(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var r = n.get(t);
			if (r === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ P(i, s));
					n.set(t, e), Ht(a);
				}
			} else I(r, i), Ht(a);
			return !0;
		},
		get(t, r, a) {
			if (r === me) return e;
			var o = n.get(r), c = r in t;
			if (o === void 0 && (!c || f(t, r)?.writable) && (o = l(() => /* @__PURE__ */ P(Wt(c ? t[r] : i), s)), n.set(r, o)), o !== void 0) {
				var u = Q(o);
				return u === i ? void 0 : u;
			}
			return Reflect.get(t, r, a);
		},
		getOwnPropertyDescriptor(e, t) {
			var r = Reflect.getOwnPropertyDescriptor(e, t);
			if (r && "value" in r) {
				var a = n.get(t);
				a && (r.value = Q(a));
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
			if (t === me) return !0;
			var r = n.get(t), a = r !== void 0 && r.v !== i || Reflect.has(e, t);
			return (r !== void 0 || K !== null && (!a || f(e, t)?.writable)) && (r === void 0 && (r = l(() => /* @__PURE__ */ P(a ? Wt(e[t]) : i, s)), n.set(t, r)), Q(r) === i) ? !1 : a;
		},
		set(e, t, o, c) {
			var u = n.get(t), d = t in e;
			if (r && t === "length") for (var p = o; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ P(i, s)), n.set(p + "", m)) : I(m, i);
			}
			if (u === void 0) (!d || f(e, t)?.writable) && (u = l(() => /* @__PURE__ */ P(void 0, s)), I(u, Wt(o)), n.set(t, u));
			else {
				d = u.v !== i;
				var h = l(() => Wt(o));
				I(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, o), !d) {
				if (r && typeof t == "string") {
					var _ = n.get("length"), ee = Number(t);
					Number.isInteger(ee) && ee >= _.v && I(_, ee + 1);
				}
				Ht(a);
			}
			return !0;
		},
		ownKeys(e) {
			Q(a);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== i;
			});
			for (var [r, o] of n) o.v !== i && !(r in e) && t.push(r);
			return t;
		},
		setPrototypeOf() {
			De();
		}
	});
}
var Gt, Kt, qt, Jt;
function Yt() {
	if (Gt === void 0) {
		Gt = window, Kt = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		qt = f(t, "firstChild").get, Jt = f(t, "nextSibling").get, _(e) && (e.__click = void 0, e.__className = void 0, e.__attributes = null, e.__style = void 0, e.__e = void 0), _(n) && (n.__t = void 0);
	}
}
function Xt(e = "") {
	return document.createTextNode(e);
}
/* @__NO_SIDE_EFFECTS__ */
function Zt(e) {
	return qt.call(e);
}
/* @__NO_SIDE_EFFECTS__ */
function Qt(e) {
	return Jt.call(e);
}
function L(e, t) {
	if (!C) return /* @__PURE__ */ Zt(e);
	var n = /* @__PURE__ */ Zt(w);
	if (n === null) n = w.appendChild(Xt());
	else if (t && n.nodeType !== 3) {
		var r = Xt();
		return n?.before(r), T(r), r;
	}
	return t && nn(n), T(n), n;
}
function R(e, t = 1, n = !1) {
	let r = C ? w : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ Qt(r);
	if (!C) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = Xt();
			return r === null ? i?.after(a) : r.before(a), T(a), a;
		}
		nn(r);
	}
	return T(r), r;
}
function $t(e) {
	e.textContent = "";
}
function en() {
	return !e || N !== null ? !1 : (K.f & oe) !== 0;
}
function tn(e, t, n) {
	let r = n ? { is: n } : void 0;
	return document.createElementNS(t ?? "http://www.w3.org/1999/xhtml", e, r);
}
function nn(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var rn = !1;
function an() {
	rn || (rn = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t.__on_r?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function on(e) {
	var t = U, n = K;
	G(null), q(null);
	try {
		return e();
	} finally {
		G(t), q(n);
	}
}
function sn(e, t, n, r = n) {
	e.addEventListener(t, () => on(n));
	let i = e.__on_r;
	i ? e.__on_r = () => {
		i(), r(!0);
	} : e.__on_r = () => r(!0), an();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function cn(e) {
	K === null && (U === null && Se(e), xe()), H && be(e);
}
function ln(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function z(e, t) {
	var n = K;
	n !== null && n.f & 8192 && (e |= ie);
	var r = {
		ctx: D,
		deps: null,
		nodes: null,
		f: e | y | 512,
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
	j?.register_created_effect(r);
	var i = r;
	if (e & 4) st === null ? dt.ensure().schedule(r) : st.push(r);
	else if (t !== null) {
		try {
			Kn(r);
		} catch (e) {
			throw V(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= ce));
	}
	if (i !== null && (i.parent = n, n !== null && ln(i, n), U !== null && U.f & 2 && !(e & 64))) {
		var a = U;
		(a.effects ??= []).push(i);
	}
	return r;
}
function un() {
	return U !== null && !W;
}
function dn(e) {
	let t = z(8, null);
	return k(t, v), t.teardown = e, t;
}
function fn(e) {
	cn("$effect");
	var t = K.f;
	if (!U && t & 32 && !(t & 32768)) {
		var n = D;
		(n.e ??= []).push(e);
	} else return pn(e);
}
function pn(e) {
	return z(4 | le, e);
}
function mn(e) {
	return cn("$effect.pre"), z(8 | le, e);
}
function hn(e) {
	dt.ensure();
	let t = z(64 | x, e);
	return () => {
		V(t);
	};
}
function gn(e) {
	dt.ensure();
	let t = z(64 | x, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? En(t, () => {
			V(t), n(void 0);
		}) : (V(t), n(void 0));
	});
}
function _n(e) {
	return z(fe | x, e);
}
function vn(e, t = 0) {
	return z(8 | t, e);
}
function yn(e, t = [], n = [], r = []) {
	wt(r, t, n, (t) => {
		z(8, () => e(...t.map(Q)));
	});
}
function bn(e, t = 0) {
	return z(16 | t, e);
}
function B(e) {
	return z(32 | x, e);
}
function xn(e) {
	var t = e.teardown;
	if (t !== null) {
		let e = H, n = U;
		Nn(!0), G(null);
		try {
			t.call(null);
		} finally {
			Nn(e), G(n);
		}
	}
}
function Sn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && on(() => {
			e.abort(S);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : V(n, t), n = r;
	}
}
function Cn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || V(t), t = n;
	}
}
function V(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (wn(e.nodes.start, e.nodes.end), n = !0), k(e, se), Sn(e, t && !n), Gn(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	xn(e), e.f ^= se, e.f |= ae;
	var i = e.parent;
	i !== null && i.first !== null && Tn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function wn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ Qt(e);
		e.remove(), e = n;
	}
}
function Tn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function En(e, t, n = !0) {
	var r = [];
	Dn(e, r, !0);
	var i = () => {
		n && V(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function Dn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= ie;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = (i.f & 65536) != 0 || (i.f & 32) != 0 && (e.f & 16) != 0;
				Dn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function On(e) {
	kn(e, !0);
}
function kn(e, t) {
	if (e.f & 8192) {
		e.f ^= ie, e.f & 1024 || (k(e, y), dt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = (n.f & 65536) != 0 || (n.f & 32) != 0;
			kn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function An(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ Qt(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var jn = null, Mn = !1, H = !1;
function Nn(e) {
	H = e;
}
var U = null, W = !1;
function G(e) {
	U = e;
}
var K = null;
function q(e) {
	K = e;
}
var J = null;
function Pn(t) {
	U !== null && (!e || U.f & 2) && (J === null ? J = [t] : J.push(t));
}
var Y = null, X = 0, Z = null;
function Fn(e) {
	Z = e;
}
var In = 1, Ln = 0, Rn = Ln;
function zn(e) {
	Rn = e;
}
function Bn() {
	return ++In;
}
function Vn(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~ue), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (Vn(a) && Nt(a), a.wv > e.wv) return !0;
		}
		t & 512 && M === null && k(e, v);
	}
	return !1;
}
function Hn(t, n, r = !0) {
	var i = t.reactions;
	if (i !== null && !(!e && J !== null && c.call(J, t))) for (var a = 0; a < i.length; a++) {
		var o = i[a];
		o.f & 2 ? Hn(o, n, !1) : n === o && (r ? k(o, y) : o.f & 1024 && k(o, b), _t(o));
	}
}
function Un(e) {
	var t = Y, n = X, r = Z, i = U, a = J, o = D, s = W, c = Rn, l = e.f;
	Y = null, X = 0, Z = null, U = l & 96 ? null : e, J = null, Ve(e.ctx), W = !1, Rn = ++Ln, e.ac !== null && (on(() => {
		e.ac.abort(S);
	}), e.ac = null);
	try {
		e.f |= de;
		var u = e.fn, d = u();
		e.f |= oe;
		var f = e.deps, p = j?.is_fork;
		if (Y !== null) {
			var m;
			if (p || Gn(e, X), f !== null && X > 0) for (f.length = X + Y.length, m = 0; m < Y.length; m++) f[X + m] = Y[m];
			else e.deps = f = Y;
			if (un() && e.f & 512) for (m = X; m < f.length; m++) (f[m].reactions ??= []).push(e);
		} else !p && f !== null && X < f.length && (Gn(e, X), f.length = X);
		if (We() && Z !== null && !W && f !== null && !(e.f & 6146)) for (m = 0; m < Z.length; m++) Hn(Z[m], e);
		if (i !== null && i !== e) {
			if (Ln++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Ln;
			if (t !== null) for (let e of t) e.rv = Ln;
			Z !== null && (r === null ? r = Z : r.push(...Z));
		}
		return e.f & 8388608 && (e.f ^= pe), d;
	} catch (e) {
		return Je(e);
	} finally {
		e.f ^= de, Y = t, X = n, Z = r, U = i, J = a, Ve(o), W = s, Rn = c;
	}
}
function Wn(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var r = s.call(n, e);
		if (r !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[r] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (Y === null || !c.call(Y, t))) {
		var o = t;
		o.f & 512 && (o.f ^= 512, o.f &= ~ue), o.v !== i && Ze(o), Pt(o), Gn(o, 0);
	}
}
function Gn(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) Wn(e, n[r]);
}
function Kn(e) {
	var t = e.f;
	if (!(t & 16384)) {
		k(e, v);
		var n = K, r = Mn;
		K = e, Mn = !0;
		try {
			t & 16777232 ? Cn(e) : Sn(e), xn(e);
			var i = Un(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = In;
		} finally {
			Mn = r, K = n;
		}
	}
}
async function qn() {
	if (e) return new Promise((e) => {
		requestAnimationFrame(() => e()), setTimeout(() => e());
	});
	await Promise.resolve(), ft();
}
function Q(e) {
	var t = (e.f & 2) != 0;
	if (jn?.add(e), U !== null && !W && !(K !== null && K.f & 16384) && (J === null || !c.call(J, e))) {
		var n = U.deps;
		if (U.f & 2097152) e.rv < Ln && (e.rv = Ln, Y === null && n !== null && n[X] === e ? X++ : Y === null ? Y = [e] : Y.push(e));
		else {
			(U.deps ??= []).push(e);
			var r = e.reactions;
			r === null ? e.reactions = [U] : c.call(r, U) || r.push(U);
		}
	}
	if (H && Lt.has(e)) return Lt.get(e);
	if (t) {
		var i = e;
		if (H) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || Yn(i)) && (a = Mt(i)), Lt.set(i, a), a;
		}
		var o = (i.f & 512) == 0 && !W && U !== null && (Mn || (U.f & 512) != 0), s = (i.f & oe) === 0;
		Vn(i) && (o && (i.f |= 512), Nt(i)), o && !s && (Ft(i), Jn(i));
	}
	if (M?.has(e)) return M.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function Jn(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (Ft(t), Jn(t));
}
function Yn(e) {
	if (e.v === i) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (Lt.has(t) || t.f & 2 && Yn(t)) return !0;
	return !1;
}
function Xn(e) {
	var t = W;
	try {
		return W = !0, e();
	} finally {
		W = t;
	}
}
function Zn(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (me in e) Qn(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && me in n && Qn(n);
		}
	}
}
function Qn(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			Qn(e[n], t);
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
var $n = Symbol("events"), er = /* @__PURE__ */ new Set(), tr = /* @__PURE__ */ new Set();
function nr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || ar.call(t, e), !e.cancelBubble) return on(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? O(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function rr(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = nr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && dn(() => {
		t.removeEventListener(e, o, a);
	});
}
var ir = null;
function ar(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	ir = e;
	var o = 0, s = ir === e && e[$n];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[$n] = t;
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
		var u = U, f = K;
		G(null), q(null);
		try {
			for (var p, m = []; a !== null;) {
				var h = a.assignedSlot || a.parentNode || a.host || null;
				try {
					var g = a[$n]?.[r];
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
			e[$n] = t, delete e.currentTarget, G(u), q(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var or = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function sr(e) {
	return or?.createHTML(e) ?? e;
}
function cr(e) {
	var t = tn("template");
	return t.innerHTML = sr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function lr(e, t) {
	var n = K;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/* @__NO_SIDE_EFFECTS__ */
function ur(e, t) {
	var n = (t & 1) != 0, r = (t & 2) != 0, i, a = !e.startsWith("<!>");
	return () => {
		if (C) return lr(w, null), w;
		i === void 0 && (i = cr(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ Zt(i)));
		var t = r || Kt ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ Zt(t), s = t.lastChild;
			lr(o, s);
		} else lr(t, t);
		return t;
	};
}
function $(e, t) {
	if (C) {
		var n = K;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = w), Pe();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var dr = ["touchstart", "touchmove"];
function fr(e) {
	return dr.includes(e);
}
function pr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e.__t ??= e.nodeValue) && (e.__t = n, e.nodeValue = `${n}`);
}
function mr(e, t) {
	return _r(e, t);
}
function hr(e, t) {
	Yt(), t.intro = t.intro ?? !1;
	let n = t.target, i = C, a = w;
	try {
		for (var o = /* @__PURE__ */ Zt(n); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ Qt(o);
		if (!o) throw r;
		Ne(!0), T(o);
		let i = _r(e, {
			...t,
			anchor: o
		});
		return Ne(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== r && console.warn("Failed to hydrate: ", i), t.recover === !1 && we(), Yt(), $t(n), Ne(!1), mr(e, t);
	} finally {
		Ne(i), T(a);
	}
}
var gr = /* @__PURE__ */ new Map();
function _r(e, { target: t, anchor: n, props: i = {}, events: a, context: o, intro: s = !0, transformError: c }) {
	Yt();
	var u = void 0, d = gn(() => {
		var s = n ?? t.appendChild(Xt());
		St(s, { pending: () => {} }, (t) => {
			He({});
			var n = D;
			if (o && (n.c = o), a && (i.$$events = a), C && lr(t, null), u = e(t, i) || {}, C && (K.nodes.end = w, w === null || w.nodeType !== 8 || w.data !== "]")) throw je(), r;
			Ue();
		}, c);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = fr(r);
					for (let e of [t, document]) {
						var a = gr.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), gr.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, ar, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(l(er)), tr.add(f), () => {
			for (var e of d) for (let n of [t, document]) {
				var r = gr.get(n), i = r.get(e);
				--i == 0 ? (n.removeEventListener(e, ar), r.delete(e), r.size === 0 && gr.delete(n)) : r.set(e, i);
			}
			tr.delete(f), s !== n && s.parentNode?.removeChild(s);
		};
	});
	return vr.set(u, d), u;
}
var vr = /* @__PURE__ */ new WeakMap();
function yr(e, t) {
	let n = vr.get(e);
	return n ? (vr.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var br = class {
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
			if (n) On(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
			}
			for (let [t, n] of this.#e) {
				if (this.#e.delete(t), t === e) break;
				let r = this.#n.get(n);
				r && (V(r.effect), this.#n.delete(n));
			}
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = document.createDocumentFragment();
						An(r, t), t.append(Xt()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else V(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), En(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (V(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = j, r = en();
		if (t && !this.#t.has(e) && !this.#n.has(e)) if (r) {
			var i = document.createDocumentFragment(), a = Xt();
			i.append(a), this.#n.set(e, {
				effect: B(() => t(a)),
				fragment: i
			});
		} else this.#t.set(e, B(() => t(this.anchor)));
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else C && (this.anchor = w), this.#a(n);
	}
};
function xr(e) {
	D === null && ve("onMount"), t && D.l !== null ? Sr(D).m.push(e) : fn(() => {
		let t = Xn(e);
		if (typeof t == "function") return t;
	});
}
function Sr(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function Cr(e, t, n = !1) {
	var r;
	C && (r = w, Pe());
	var i = new br(e), a = n ? ce : 0;
	function o(e, t) {
		if (C) {
			var n = Le(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Ie();
				T(a), i.anchor = a, Ne(!1), i.ensure(e, t), Ne(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	bn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var wr = Symbol("is custom element"), Tr = Symbol("is html"), Er = _e ? "link" : "LINK";
function Dr(e) {
	if (C) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Or(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Or(e, "checked", null), e.checked = r;
				}
			}
		};
		e.__on_r = n, O(n), an();
	}
}
function Or(e, t, n, r) {
	var i = kr(e);
	C && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Er) || i[t] !== (i[t] = n) && (t === "loading" && (e[ge] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && jr(e).includes(t) ? e[t] = n : e.setAttribute(t, n));
}
function kr(e) {
	return e.__attributes ??= {
		[wr]: e.nodeName.includes("-"),
		[Tr]: e.namespaceURI === a
	};
}
var Ar = /* @__PURE__ */ new Map();
function jr(e) {
	var t = e.getAttribute("is") || e.nodeName, n = Ar.get(t);
	if (n) return n;
	Ar.set(t, n = []);
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = p(i), r) r[o].set && n.push(o);
		i = g(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function Mr(t, n, r = n) {
	var i = /* @__PURE__ */ new WeakSet();
	sn(t, "input", async (e) => {
		var a = e ? t.defaultValue : t.value;
		if (a = Nr(t) ? Pr(a) : a, r(a), j !== null && i.add(j), await qn(), a !== (a = n())) {
			var o = t.selectionStart, s = t.selectionEnd, c = t.value.length;
			if (t.value = a ?? "", s !== null) {
				var l = t.value.length;
				o === s && s === c && l > c ? (t.selectionStart = l, t.selectionEnd = l) : (t.selectionStart = o, t.selectionEnd = Math.min(s, l));
			}
		}
	}), (C && t.defaultValue !== t.value || Xn(n) == null && t.value) && (r(Nr(t) ? Pr(t.value) : t.value), j !== null && i.add(j)), vn(() => {
		var r = n();
		if (t === document.activeElement) {
			var a = e ? rt : j;
			if (i.has(a)) return;
		}
		Nr(t) && r === Pr(t.value) || t.type === "date" && !r && !t.value || r !== t.value && (t.value = r ?? "");
	});
}
function Nr(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function Pr(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function Fr(e = !1) {
	let t = D, n = t.l.u;
	if (!n) return;
	let r = () => Zn(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ Ot(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Q(i);
	}
	n.b.length && mn(() => {
		Ir(t, r), ne(n.b);
	}), fn(() => {
		let e = Xn(() => n.m.map(te));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && fn(() => {
		Ir(t, r), ne(n.a);
	});
}
function Ir(e, t) {
	if (e.l.s) for (let t of e.l.s) Q(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function Lr(e, n, r, i) {
	var a = !t || (r & 2) != 0, o = (r & 8) != 0, s = (r & 16) != 0, c = i, l = !0, u = () => (l && (l = !1, c = s ? Xn(i) : i), c);
	let d;
	if (o) {
		var p = me in e || he in e;
		d = f(e, n)?.set ?? (p && n in e ? (t) => e[n] = t : void 0);
	}
	var m, h = !1;
	o ? [m, h] = nt(() => e[n]) : m = e[n], m === void 0 && i !== void 0 && (m = u(), d && (a && Te(n), d(m)));
	var g = a ? () => {
		var t = e[n];
		return t === void 0 ? u() : (l = !0, t);
	} : () => {
		var t = e[n];
		return t !== void 0 && (c = void 0), t === void 0 ? c : t;
	};
	if (a && !(r & 4)) return g;
	if (d) {
		var _ = e.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || _ || h) && d(t ? g() : e), e) : g();
		});
	}
	var ee = !1, te = (r & 1 ? Ot : At)(() => (ee = !1, g()));
	o && Q(te);
	var ne = K;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Q(te) : a && o ? Wt(e) : e;
			return I(te, n), ee = !0, c !== void 0 && (c = n), e;
		}
		return H && ee || ne.f & 16384 ? te.v : Q(te);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function Rr(e) {
	return new zr(e);
}
var zr = class {
	#e;
	#t;
	constructor(t) {
		var n = /* @__PURE__ */ new Map(), r = (e, t) => {
			var r = /* @__PURE__ */ F(t, !1, !1);
			return n.set(e, r), r;
		};
		let i = new Proxy({
			...t.props || {},
			$$events: {}
		}, {
			get(e, t) {
				return Q(n.get(t) ?? r(t, Reflect.get(e, t)));
			},
			has(e, t) {
				return t === he ? !0 : (Q(n.get(t) ?? r(t, Reflect.get(e, t))), Reflect.has(e, t));
			},
			set(e, t, i) {
				return I(n.get(t) ?? r(t, i), i), Reflect.set(e, t, i);
			}
		});
		this.#t = (t.hydrate ? hr : mr)(t.component, {
			target: t.target,
			anchor: t.anchor,
			props: i,
			context: t.context,
			intro: t.intro ?? !1,
			recover: t.recover,
			transformError: t.transformError
		}), !e && (!t?.props?.$$host || t.sync === !1) && ft(), this.#e = i.$$events;
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
			yr(this.#t);
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
}, Br;
typeof HTMLElement == "function" && (Br = class extends HTMLElement {
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
					let n = tn("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = Hr(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = Vr(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = Rr({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = hn(() => {
				vn(() => {
					this.$$r = !0;
					for (let e of u(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = Vr(e, this.$$d[e], this.$$p_d, "toAttribute");
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
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = Vr(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
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
function Vr(e, t, n, r) {
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
function Hr(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function Ur(e, t, n, r, i, a) {
	let o = class extends Br {
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
				n = Vr(e, n, t), this.$$d[e] = n;
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
//#region SlskdCard.svelte
var Wr = /* @__PURE__ */ ur("<span class=\"text-[12px] px-2 py-1 rounded-[4px] bg-[#00e676]/20 text-[#00e676]\">● Connected</span>"), Gr = /* @__PURE__ */ ur("<span class=\"text-[12px] px-2 py-1 rounded-[4px] bg-[#ff9800]/20 text-[#ff9800]\">⚠ Disconnected</span>"), Kr = /* @__PURE__ */ ur("<span class=\"status-badge active-client\">● Active</span>"), qr = /* @__PURE__ */ ur("<button class=\"btn-sm btn-secondary active:scale-95 transition-all duration-200\">Activate</button>"), Jr = /* @__PURE__ */ ur("<div class=\"p-5 text-center text-secondary\">Loading...</div>"), Yr = /* @__PURE__ */ ur("<button class=\"px-4 py-2 bg-white/10 text-primary border border-white/20 rounded-global transition-colors hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95\"> </button>"), Xr = /* @__PURE__ */ ur("<div class=\"mb-6\"><h3 class=\"m-0 mb-4 text-base font-semibold\">Server Configuration</h3> <div class=\"flex flex-col gap-4\"><label class=\"flex flex-col gap-[6px]\"><span class=\"text-[13px] font-medium text-primary\">Server URL</span> <input type=\"text\" placeholder=\"http://192.168.1.100:5030\" class=\"px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent\"/> <span class=\"text-xs text-secondary mt-1\">Enter your slskd server address (include port, default :5030)</span></label> <label class=\"flex flex-col gap-[6px]\"><span class=\"text-[13px] font-medium text-primary\">Server Name (Optional)</span> <input type=\"text\" placeholder=\"My slskd Server\" class=\"px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent\"/> <span class=\"text-xs text-secondary mt-1\">Friendly name for this server</span></label> <label class=\"flex flex-col gap-[6px]\"><span class=\"text-[13px] font-medium text-primary\">API Key</span> <div class=\"input-with-toggle\"><input placeholder=\"Enter API key\" class=\"px-3 py-2 bg-background border border-border rounded-global text-sm text-primary w-full box-border focus:outline-none focus:border-accent\"/> <button type=\"button\" class=\"toggle-btn active:scale-95 transition-all duration-200\"> </button></div> <span class=\"text-xs text-secondary mt-1\">API key from slskd settings (Options → Security → API Keys)</span></label> <div class=\"flex gap-3 flex-wrap\"><button class=\"px-4 py-2 bg-accent text-black font-medium rounded-global transition-colors hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95\"> </button> <!></div></div></div>"), Zr = /* @__PURE__ */ ur("<section class=\"p-6 bg-surface backdrop-blur-md border border-glass-border rounded-global mb-4\"><div class=\"flex justify-between items-center mb-5 pb-3 border-b border-glass-border\"><div class=\"flex items-center gap-3\"><h2 class=\"m-0 text-xl font-semibold\">slskd</h2> <span class=\"text-[12px] px-2 py-1 rounded-[4px] bg-[#ba6415]/20 text-[#ba6415]\">Download Client</span> <!> <!></div> <div class=\"header-right\"><!> <button class=\"bg-transparent text-[#ba6415] px-2 py-1 hover:underline active:scale-95 transition-all duration-200\"> </button></div></div> <!></section>");
function Qr(e, t) {
	He(t, !1);
	let n = Lr(t, "apiBase", 12, ""), r = /* @__PURE__ */ F(""), i = /* @__PURE__ */ F(""), a = /* @__PURE__ */ F(""), o = /* @__PURE__ */ F(!1), s = /* @__PURE__ */ F(!0), c = /* @__PURE__ */ F(!1), l = /* @__PURE__ */ F(!1), u = /* @__PURE__ */ F(!1), d = /* @__PURE__ */ F(!1), f = /* @__PURE__ */ F(!1), p = !1, m = /* @__PURE__ */ F(!1);
	xr(async () => {
		await _(), await h(), I(s, !1);
	});
	async function h() {
		try {
			I(m, (await fetch(`${n()}/providers/download-clients/active`)).data.active_client === "slskd");
		} catch (e) {
			console.error("Failed to check active status:", e);
		}
	}
	async function g() {
		try {
			await fetch(`${n()}/providers/download-clients/activate`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ client: "slskd" })
			}), I(m, !0), console.log("Slskd activated as download client");
		} catch (e) {
			console.error("Failed to activate client:", e), console.error("Failed to activate client");
		}
	}
	async function _() {
		try {
			let e = await fetch(`${n()}/providers/soulseek/settings`);
			e.data && (I(r, e.data.slskd_url || ""), I(a, e.data.server_name || ""), I(i, e.data.api_key || ""), I(f, e.data.has_api_key || !1), I(o, e.data.configured || !1));
		} catch (e) {
			console.error("Failed to load slskd settings:", e), console.error("Failed to load slskd settings");
		}
	}
	async function ee() {
		if (!Q(r).trim()) {
			console.error("Server URL is required");
			return;
		}
		try {
			I(c, !0);
			let e = {
				slskd_url: Q(r),
				server_name: Q(a)
			};
			Q(i) && Q(i) !== "****" && (e.api_key = Q(i)), await fetch(`${n()}/providers/soulseek/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			}), console.log("slskd settings saved"), await _();
		} catch (e) {
			console.error("Failed to save slskd settings:", e), console.error("Failed to save settings");
		} finally {
			I(c, !1);
		}
	}
	async function te() {
		if (!Q(r).trim()) {
			console.error("Server URL is required");
			return;
		}
		if (!Q(f) && !Q(i).trim()) {
			console.error("API Key is required");
			return;
		}
		try {
			I(l, !0);
			let e = await fetch(`${n()}/providers/soulseek/connection/test`, { method: "POST" });
			e.data?.success ? (console.log("slskd connection successful!"), I(o, !0)) : (console.error(e.data?.error || "Connection failed"), I(o, !1));
		} catch (e) {
			console.error("Failed to test slskd connection:", e), console.error("Connection test failed"), I(o, !1);
		} finally {
			I(l, !1);
		}
	}
	async function ne() {
		let e = !Q(d);
		if (I(d, e), e && Q(f) && Q(i) === "****" && !p) try {
			let e = await fetch(`${n()}/providers/soulseek/settings/key`);
			e.data && e.data.api_key ? (I(i, e.data.api_key), p = !0) : (console.error("Failed to reveal API key"), I(d, !1));
		} catch (e) {
			console.error("Failed to fetch API key:", e), console.error("Unable to reveal API key"), I(d, !1);
		}
		!e && p && (I(i, "****"), p = !1);
	}
	var re = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), ft();
		}
	};
	Fr();
	var v = Zr(), y = L(v), b = L(y), ie = R(L(b), 4), ae = (e) => {
		$(e, Wr());
	}, oe = (e) => {
		$(e, Gr());
	};
	Cr(ie, (e) => {
		Q(o) ? e(ae) : Q(r) && e(oe, 1);
	});
	var se = R(ie, 2), ce = (e) => {
		$(e, Kr());
	};
	Cr(se, (e) => {
		Q(m) && e(ce);
	}), E(b);
	var x = R(b, 2), le = L(x), ue = (e) => {
		var t = qr();
		rr("click", t, g), $(e, t);
	};
	Cr(le, (e) => {
		!Q(m) && Q(o) && e(ue);
	});
	var de = R(le, 2), fe = L(de, !0);
	E(de), E(x), E(y);
	var pe = R(y, 2), me = (e) => {
		$(e, Jr());
	}, he = (e) => {
		var t = Xr(), n = R(L(t), 2), o = L(n), s = R(L(o), 2);
		Dr(s), Fe(2), E(o);
		var u = R(o, 2), p = R(L(u), 2);
		Dr(p), Fe(2), E(u);
		var m = R(u, 2), h = R(L(m), 2), g = L(h);
		Dr(g);
		var _ = R(g, 2), re = L(_, !0);
		E(_), E(h), Fe(2), E(m);
		var v = R(m, 2), y = L(v), b = L(y, !0);
		E(y);
		var ie = R(y, 2), ae = (e) => {
			var t = Yr(), n = L(t, !0);
			E(t), yn(() => {
				t.disabled = Q(l), pr(n, Q(l) ? "Testing..." : "Test Connection");
			}), rr("click", t, te), $(e, t);
		};
		Cr(ie, (e) => {
			Q(r) && (Q(f) || Q(i)) && e(ae);
		}), E(v), E(n), E(t), yn(() => {
			Or(g, "type", Q(d) ? "text" : "password"), Or(_, "title", Q(d) ? "Hide" : "Show"), pr(re, Q(d) ? "👁️" : "👁️‍🗨️"), y.disabled = Q(c), pr(b, Q(c) ? "Saving..." : "Save Settings");
		}), Mr(s, () => Q(r), (e) => I(r, e)), Mr(p, () => Q(a), (e) => I(a, e)), Mr(g, () => Q(i), (e) => I(i, e)), rr("click", _, ne), rr("click", y, ee), $(e, t);
	};
	return Cr(pe, (e) => {
		Q(s) ? e(me) : Q(u) || e(he, 1);
	}), E(v), yn(() => pr(fe, Q(u) ? "Expand" : "Collapse")), rr("click", de, () => I(u, !Q(u))), $(e, v), Ue(re);
}
customElements.define("slskd-dashboard-card", Ur(Qr, { apiBase: {} }, [], []));
//#endregion
export { Qr as default };
